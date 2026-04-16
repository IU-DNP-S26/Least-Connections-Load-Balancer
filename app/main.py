import io

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
import uvicorn
import sys
import zipfile
import tempfile
import os


app = FastAPI()


from converters.md_to_pdf import convert_to_pdf


async def extract_archive(archive: UploadFile, path):
    archive_bytes = await archive.read()
    try:
        with zipfile.ZipFile(io.BytesIO(archive_bytes)) as zip:
            zip.extractall(path)
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail='Invalid .zip archive')
    

def find_md(dir) -> str:
    result = None
    for dirpath, _, filenames in os.walk(dir):
        for filename in filenames:
            if filename.endswith('.md'):
                if result != None:
                    raise HTTPException(status_code=400, detail='Only one .md file is allowed')
                result = os.path.join(dirpath, filename)

    if result == None:
        raise HTTPException(status_code=400, detail='No .md file found')

    return result


@app.post('/convert/md/to-pdf')
async def md_to_pdf(archive: UploadFile = File(...)):
    archive_name = str(archive.filename)
    if not archive_name.endswith('.zip'):
        detail='Unknown archive extension\nExpected .zip archive'
        raise HTTPException(status_code=400, detail=detail)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        await extract_archive(archive, tmpdir)
        path_to_md = find_md(tmpdir)
        md_filename = os.path.basename(path_to_md)
        result_filename = os.path.splitext(md_filename)[0] + '.pdf'

        result_path = convert_to_pdf(path_to_md)
        return FileResponse(
            path=result_filename,
            media_type='application/pdf',
            filename=result_path
        )
    

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage: main.py <port>')
        sys.exit(1)

    port = int(sys.argv[1])
    uvicorn.run('main:app', host='0.0.0.0', port=port, reload=True)
