## Konvertik — Markdown-to-PDF converter

### About
**Konvertik** is a lightweight Markdown-to-PDF converter which is heavily inspired by the **System and Network Administration\*** course, where weekly PDF reports were required.

**\*** _Innopolis University, Spring 2026_

### Features
- GitHub-like PDF styling
- Minimal and easy-to-read code base
- Fast setup with Docker

### Why it exists
**Konvertik** is made specifically for the **Distributed and Network Programming** course _(Innopolis University, S26)_.

It serves as a test backend application for a self-written load balancer. The application executes a CPU-bound task, demonstrating the effect of load distribution. Therefore, **Konvertik** is highly suitable for the project.

### Deployment
You can deploy **Konvertik** using Docker.

#### Install Docker on your machine
- **Ubuntu:** `sudo apt install docker`
- **MacOS:** `homebrew install docker`

#### Clone the repository
```bash
git clone https://github.com/IU-DNP-S26/Least-Connections-Load-Balancer.git
cd Least-Connections-Load-Balancer
```

#### Build the image
```bash
docker build --tag konvertik .
```

#### Run the container
```bash
docker run -p 8080:80 konvertik
```

You can expose a different port if needed:
```bash
docker run -p <port>:80 konvertik
```

### Usage

#### Change into a directory with a Markdown file

```bash
cd /directory/with/markdown/file
```

#### Create a zip archive

```bash
zip test.zip -r .
```

#### Send the zip archive to the server

```bash
curl -X POST http://127.0.0.1:8080/convert/md/to-pdf -F "archive=@test.zip" --output result.pdf
```

After the archive is sent to the server, the result pdf will be composed and sent back to you.