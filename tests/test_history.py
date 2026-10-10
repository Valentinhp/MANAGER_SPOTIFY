from concurrent.futures import ThreadPoolExecutor
import pytest
from src.utils import ai_history

def test_history_preserves_concurrent_generations_and_playlist(tmp_path,monkeypatch):
    monkeypatch.setattr(ai_history,'HISTORY_FILE',tmp_path/'ai_history.json')
    with ThreadPoolExecutor(max_workers=4) as pool:
        ids=list(pool.map(lambda i:ai_history.save_generation(str(i),[{'title':'X','artist':'Y'}]),range(8)))
    ai_history.attach_playlist(ids[3],'playlist')
    rows=ai_history.load_history()
    assert len(rows)==8
    assert next(r for r in rows if r['id']==ids[3])['playlist_id']=='playlist'

def test_corrupt_history_is_not_overwritten(tmp_path,monkeypatch):
    path=tmp_path/'ai_history.json';path.write_text('broken',encoding='utf-8')
    monkeypatch.setattr(ai_history,'HISTORY_FILE',path)
    with pytest.raises(RuntimeError):ai_history.save_generation('test',[])
    assert path.read_text(encoding='utf-8')=='broken'
