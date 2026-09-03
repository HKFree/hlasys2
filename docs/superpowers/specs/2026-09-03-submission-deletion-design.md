# Submission deletion (soft delete)

**Date:** 2026-09-03 · **Status:** approved, pending implementation

## Problem

A submitter or a member of a proposal's target committee needs to remove a proposal
that should not have been filed, provided it has not yet been decided. Removal must be
recoverable at the data layer, auditable, and must not destroy voting history.

## Rules

A proposal is deletable when **all** hold:

- `proposal.deleted IS NULL`
- `proposal.decided IS NULL`
- the acting user is the author (`user_id == author_id`), **or** is a decider on a
  proposal whose `type` is in `DECIDER_DELETE_TYPES`

`DECIDER_DELETE_TYPES` defaults to `[0, 1, 2]` (VV, SO, PD). CS is excluded
deliberately: it has 116 deciders, which would make deletion of another member's
proposal too broadly available. No admin override. Existing votes do not block
deletion but are shown as a warning before confirming.

## Data model

No schema change. Deletion is a single transaction:

```python
ts = datetime.now().isoformat(sep=" ", timespec="microseconds")

db.execute(
    "UPDATE proposal SET deleted = :ts "
    "WHERE id = :id AND deleted IS NULL AND decided IS NULL",
    {"ts": ts, "id": proposal_id},
)                                  # rowcount must be 1, else abort - guards TOCTOU

db.execute(
    "INSERT INTO event (proposal_id, author_id, author_name, decision, comment, created) "
    "VALUES (:pid, :uid, :uname, NULL, :comment, :ts)",
    {...},
)
db.commit()
```

`decision IS NULL` with a non-null `comment` satisfies the existing CHECK on `event`.
The event is attributed to the acting user, following `change_state`
(`proposals.py:296`) rather than the `author_id=0 / 'Systém'` form used by
`check_proposal_status`.

Comment text: `Návrh smazal {name}.` plus ` Důvod: {reason}` when a reason was supplied.

**Deleter lookup.** The deletion event is identified by exact timestamp equality with
`proposal.deleted`. Both are written from the same Python value, at microsecond
precision, so the match is unambiguous and cannot be forged by a user - a user can
write `event.created` only via the DB default, and cannot set `proposal.deleted` at all.

```sql
(SELECT e.author_name FROM event e
   WHERE e.proposal_id = p.id AND e.created = p.deleted LIMIT 1) AS deleted_by_name
```

This coupling is implicit and must be documented at both the write and read sites. The
237 pre-existing rows hidden during the 2005-data migration have no matching event and
resolve to `NULL`, rendering as `—`.

## Permissions

```python
def can_delete_proposal(user_id: int, proposal: dict) -> bool:
    if proposal["deleted"] is not None or proposal["decided"] is not None:
        return False
    if int(proposal["author_id"]) == user_id:
        return True
    if int(proposal["type"]) in getattr(config, "DECIDER_DELETE_TYPES", [0, 1, 2]):
        deciders = proposal["deciders"]
        if isinstance(deciders, str):
            deciders = json.loads(deciders)
        return str(user_id) in deciders          # dict key, never substring
    return False
```

Two details. The helper accepts `deciders` either raw or parsed, because
`view_proposal` parses it in place at `proposals.py:172` while other callers do not.
And `DECIDER_DELETE_TYPES` is read through `getattr` with a default: `config.py` is
bind-mounted read-only in production (`docker-compose.prod.yaml`), so the deployed
config will not contain the new key on first deploy.

## Code structure

| File | Change |
|---|---|
| `util.py` | add `can_delete_proposal()` |
| `deletion.py` | **new** blueprint mirroring `votes.py`: `_load_deletable_proposal()`, `GET/POST /proposal/<id>/delete` |
| `proposals.py` | extract `_build_overview_query()`; koš mode in `overview()`; `view_proposal` no longer redirects deleted proposals |
| `forms.py` | `DeleteProposalForm` - optional `reason` TextArea, CSRF |
| `users.py` | timeline and its existence probe exclude `deleted IS NOT NULL` |
| `config.example.py` | document `DECIDER_DELETE_TYPES = [0, 1, 2]` |
| `__init__.py` | register the new blueprint |
| `templates/proposals/delete.html` | **new** confirmation page |
| `templates/proposals/overview.html` | koš toggle, conditional columns |
| `templates/proposals/one.html` | deleted banner, hide state buttons |
| `templates/proposals/decisions.html` | delete button, hide actions when deleted |
| `tests/test_deletion.py` | **new** |

`_build_overview_query(filter, search_query, deleted, page, limit)` returns
`(where_clause, params, order_by, limit, offset)`. Callers compose their own SELECT:
normal mode keeps today's two-step ID-then-aggregate query, koš mode uses a single
simpler query since it displays no vote counts.

## UI

**Koš** - `/overview/<filter>?deleted=1`, toggle appended to the existing filter strip,
search box hidden, ordered `deleted DESC` so real deletions always sort above the
single-timestamp legacy batch.

```
+----------------------------------------------------------------------+
|  X Predstavenstvo Druzstva   V Vykonny Vybor   X Clenove spolku       |
|  X Clenove druzstva   X Spravce Oblasti (archiv)   V Kos              |
|                                                                       |
|  Kos - Vykonny Vybor                          Strana 1 z 10           |
|  Navrh                    Vytvoreno  Navrhovatel  Smazal   Smazano    |
|  -------------------------------------------------------------------  |
|  Test omylem zalozeny     11.03.     Pithart      Pithart  11.03.14:22|
|  Duplicitni navrh         08.03.     Novak        Kriz     09.03.09:10|
|  Prvni navrh              20.06.05   -            -        28.01.21:29|
+----------------------------------------------------------------------+
```

The `Stav` column is replaced by `Smazal` and `Smazáno`. All five type-filter links
must propagate `?deleted=1`, since `next_filter` currently rewrites the whole filter
segment.

**Confirmation** - `GET /proposal/<id>/delete` renders, `POST` acts, giving CSRF
protection for free. Deliberately not the plain-GET-link pattern used by
`change_state`.

```
+- /proposal/1234/delete -----------------------------------------------+
|  Opravdu smazat navrh?                                                |
|  "Nakup switche pro Slezske predmesti"                                |
|  navrh 1234 pro Vykonny Vybor spolku - vlozil Novak 12.03.2026        |
|                                                                       |
|  ! U navrhu uz jsou 3 hlasy (2 PRO, 1 PROTI).                         |
|    Smazanim zmizi navrh i s nimi z prehledu.                          |
|                                                                       |
|  Duvod smazani (nepovinny)                                            |
|  +-----------------------------------------------------------------+  |
|  | Duplicita, viz navrh 1230                                       |  |
|  +-----------------------------------------------------------------+  |
|  [ Smazat navrh ]  [ Zpet ]                                           |
|     ^ red                                                             |
|  Smazani nelze vratit zpet.                                           |
+-----------------------------------------------------------------------+
```

**Deleted detail page** - visible read-only to any logged-in user:

```
+- /proposal/1234 ------------------------------------------------------+
| +===================================================================+ |
| | Navrh byl smazan 11.03.2026 v 14:22 uzivatelem Pithart            | |
| |    Duvod: Duplicita, viz navrh 1230                               | |
| +===================================================================+ |
|  ...popis, cena, hlasy - vse read-only...                             |
|  X no vote buttons   X no comment button   X no state buttons         |
|  Historie navrhu - including the deletion event                       |
+-----------------------------------------------------------------------+
```

For legacy rows the banner degrades to `Návrh byl smazán 28.01.2026` with no actor and
no reason.

**Delete button** sits in the `d-vote-btn` row beside "Přidat komentář",
danger-styled, rendered only when `can_delete_proposal()` passes.

## Ripple effects and error handling

- `proposals.py:31` - a numeric search matching a deleted proposal currently redirects
  into a bounce loop; resolved once the detail page renders deleted proposals
- `votes.py:96` and `add_comment` continue to hard-block server-side, independent of
  what templates hide
- Deleting an already-deleted or already-decided proposal: the guard is in the
  `UPDATE ... WHERE` clause and re-checked via `rowcount`, so a double submit produces
  one flash and no second event
- Permission failure: flash + redirect to the proposal, matching `change_state`'s
  convention

## Testing

`tests/test_deletion.py`, run with `pytest` (added as a dev dependency):

- permission matrix for `can_delete_proposal` - author, decider on VV/SO/PD, decider on
  CS, non-member, already decided, already deleted
- regression: user `27` must **not** pass the decider check on a proposal whose
  deciders include `277`
- `_build_overview_query` in normal vs. koš mode - WHERE clause, ORDER BY, pagination

Both functions are pure and need no Flask request context.

## Out of scope

Restore/undelete · Slack notification on deletion · admin override · `event.kind`
typing · a migration mechanism · the `votes.py:100` decider substring bug · markdown
support · API documentation · CI.

## Known tradeoffs

1. **Deletion is irreversible from the UI** while any VV/SO/PD decider may delete
   another member's proposal. The confirmation screen carries the weight. Restore is a
   small follow-up - the data is all retained.
2. **The deleter is derived by timestamp equality**, an implicit coupling between two
   write sites, rather than an explicit column.
3. **`votes.py:100` keeps its substring bug**, so the delete check and the vote check
   disagree slightly on who counts as a decider. Tracked separately.
4. **Legacy rows show `—` for Smazal**, since they predate the audit event.
