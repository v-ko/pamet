from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fusion.libs.entity.change import Change

from pamet.storage.file_system.repository import FSStorageRepository

REPO_DIR = Path.home() / 'pamet_server_repo'
DEBUG = True

app = FastAPI()

origins = [
    'http://localhost',
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

repo = FSStorageRepository(REPO_DIR)
repo.load_all_pages()


@app.get('/api/page/{page_id}/children')
def get_children(page_id: str):
    page = repo.page(page_id)
    if not page:
        raise HTTPException(status_code=404, detail='Page not found')

    note_dicts = []
    for note in repo.notes(page_id):
        note_dict = note.asdict()
        note_dict['type'] = type(note).__name__
        note_dicts.append(note_dict)

    arrow_dicts = []
    for arrow in repo.arrows(page_id):
        arrow_dict = arrow.asdict()
        arrow_dict['type'] = type(arrow).__name__
        arrow_dicts.append(arrow_dict)

    return {
        'notes': note_dicts,
        'arrows': arrow_dicts,
    }


@app.post('/api/page/{page_id}/changes')
async def apply_changes(request: Request):
    json_payload = await request.json()
    change_dicts = json_payload.get('changes')
    if not change_dicts:
        raise HTTPException(status_code=400, detail='No changes provided')

    try:
        changes = [Change.from_dict(change) for change in change_dicts]
    except Exception as e:
        err_message = f'Invalid change'
        if DEBUG:
            err_message += f': {e}'
        raise HTTPException(status_code=400, detail=err_message)

    failed_changes = []
    successfull_changes = []
    for change_dict in change_dicts:
        try:
            change = Change.from_dict(change_dict)
        except Exception as e:
            err_message = 'Invalid change'
            if DEBUG:
                err_message += f': {e}'
            failed_changes.append({
                'change': change_dict,
                'error': err_message,
            })
            continue

        try:
            repo.apply_change(change)
        except Exception as e:
            err_message = 'Failed to apply change'
            if DEBUG:
                err_message += f': {e}'
            failed_changes.append({
                'change': change_dict,
                'error': err_message,
            })
            continue

        successfull_changes.append(change.id)

    if not failed_changes:
        return HTTPException(status_code=207, detail={
            'applied_changes': successfull_changes,
            'errors': failed_changes,
        })
    else:
        return {
            'applied_changes': successfull_changes,
        }
