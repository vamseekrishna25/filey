# Filey - A Web-Based File Browser and Streamer

Filey is a lightweight, web-based file browser built with Python and Tornado. It provides a simple and secure interface for browsing local directories, uploading files (including nested folders via drag-and-drop), and streaming file content in real-time, similar to `tail -f`.

## Features

- **File & Directory Browsing:** Navigate your local filesystem through a clean, black-and-white themed web interface.
- **Drag-and-Drop Uploads:** Easily upload files and entire folder structures by dragging them into the browser window.
- **Real-Time File Streaming:** Open any file in streaming mode to see new lines appended in real-time, perfect for monitoring logs or other active files. The stream will also show the last 100 lines for immediate context.
- **Secure Access:** The entire application is protected by a token-based authentication system.

## Setup and Installation

1.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Run the Application:**
    ```bash
    python -m wb
    ```
    Upon starting, a unique access token will be printed to the console. Use this token to log in. The application will be served on `http://localhost:8000` by default.

## Endpoints

All endpoints (except the login page itself) require a valid authentication token, which is set as a secure cookie upon login.

### `GET /`
- **Description:** The main endpoint for browsing files and directories. It displays the contents of the current working directory.
- **Usage:** Navigate to the root URL to start browsing.

### `GET /<path:path>`
- **Description:** Renders a directory listing or a file view, depending on the path.
- **Usage:**
    - If `<path>` is a directory, it shows the contents of that directory.
    - If `<path>` is a file, it displays the file's content and provides "Download" and "Stream" options.

### `GET /login`
- **Description:** Displays the login page where you can enter your access token.

### `POST /login`
- **Description:** Handles the authentication process.
- **Body:** `token=<your_access_token>`
- **On Success:** Sets a secure cookie and redirects to `/`.
- **On Failure:** Reloads the login page with an error message.

### `POST /upload`
- **Description:** Handles file and folder uploads. This endpoint is used by the drag-and-drop interface.
- **Body:** `multipart/form-data` containing the files and the target directory.
- **Usage:** Drag files/folders into the drop zone on the directory listing page. The frontend handles the request automatically.

### `WS /stream/<path:path>`
- **Description:** A WebSocket endpoint for real-time file streaming.
- **Authentication:** Requires a valid session cookie.
- **Usage:** When a user clicks the "Stream" button, a WebSocket connection is established to this endpoint. The server will first send the last 100 lines of the file and then continue to send new lines as they are appended.