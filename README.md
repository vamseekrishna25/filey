# wb Package

`wb` is a lightweight web-based file browser built on Tornado. It lets you browse and download files from a directory through a simple web interface protected by an access token.

## Installation

Run the following command from the project root to install the package and its dependencies:

```bash
pip install .
```

## Usage

Start the server using:

```bash
python -m wb [--port PORT] [--dir DIRECTORY]
```

On startup a one-time access token is printed to the console. Navigate to `http://<host>:<port>/login` and provide this token to gain access. The default port range is 8000-9000 but you can specify a port with the `--port` flag or the `WB_PORT` environment variable. Use `--dir` (or `WB_DIR`) to serve a different directory.

Once logged in you can browse directories, download files and upload new files from the `/upload` page.

## Running Tests

Install development requirements and run `pytest`:

```bash
pip install -r requirements.txt
pytest
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
