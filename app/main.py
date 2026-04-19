from converters.md_to_pdf import convert_to_pdf
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
import uvicorn
import sys
import zipfile
import tempfile
import os
import io


app = FastAPI()


async def extract_archive(archive: UploadFile, path: str) -> None:
    """
    Extracts the archive into the provided directory.

    Args:
        archive (UploadFile): .zip archive file
        path (str): path to the directory

    Example:
        >>> extract_archive('archive.zip', 'temporary_dir')
    """
    archive_bytes = await archive.read()
    try:
        with zipfile.ZipFile(io.BytesIO(archive_bytes)) as zip:
            zip.extractall(path)
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail='Invalid .zip archive')


def find_md(dir: str) -> str:
    """
    Finds a single markdown file.

    Args:
        dir (str): search directory

    Returns:
        str: path to the found markdown file

    Raises:
        HTTPException: no markdown file was found
        or multiple markdown files were found

    Example:
        >>> find_md('temporary_dir')
    """
    result = None
    for dirpath, _, filenames in os.walk(dir):
        for filename in filenames:
            if not filename.endswith('.md'):
                continue
            # Save the path
            if result != None:  # markdown file was found before
                raise HTTPException(
                    status_code=400, detail='Only one .md file is allowed')
            result = os.path.join(dirpath, filename)

    if result == None:  # no markdown file was found
        raise HTTPException(status_code=400, detail='No .md file found')

    return result


@app.post('/convert/md/to-pdf')
async def md_to_pdf(archive: UploadFile = File(...)):
    """
    Route for converting a markdown file to PDF. 

    Args:
        archive (UploadFile): .zip archive

    Returns:
        FileResponse: the converted file

    Raises:
        HTTPException: no .zip archive was provided
        or the provided archive is invalid
    """
    # Check for the .zip archive being provided
    archive_name = str(archive.filename)
    if not archive_name.endswith('.zip'):
        detail = 'Unknown archive extension\nExpected .zip archive'
        raise HTTPException(status_code=400, detail=detail)

    # Create a temporary directory
    with tempfile.TemporaryDirectory() as tmpdir:
        await extract_archive(archive, tmpdir)

        # Find the markdown file
        # and compose the result filename
        path_to_md = find_md(tmpdir)
        md_filename = os.path.basename(path_to_md)
        result_filename = os.path.splitext(md_filename)[0] + '.pdf'

        # Convert to PDF and send back
        result_path = convert_to_pdf(path_to_md)
        return FileResponse(
            path=result_path,
            media_type='application/pdf',
            filename=result_filename
        )

@app.get('/health')
async def healthcheck():
    return {"status": "ok"}

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage: main.py <port>')
        sys.exit(1)

    port = int(sys.argv[1])
    uvicorn.run('main:app', host='0.0.0.0', port=port, reload=True)
