# HlaSys 2 for hkfree.org

A Flask + SQLite webapp for the nonprofit orgation hkfree.org z.s.

It's goal is to replace the current voting system for the organization that should have been replaced years ago...

## Running

I have created a `Dockerfile` for easy containerization. To run this app, do the following:

1. Clone repo
```bash
git clone https://code.darkne.dev/MrReactive/hlasys2.git && cd $_
```

2. Create your config files in `container-data` as per the examples.

3. Build the container image.
```bash
docker-compose build .
```

4. Run it.
```bash
docker-compose up -d
```

5. Check that it's running
```bash
curl http://localhost:5000 && echo "It works."
```

## License 

This project uses the [GNU GPLv3](https://www.gnu.org/licenses/gpl-3.0.en.html) license.

