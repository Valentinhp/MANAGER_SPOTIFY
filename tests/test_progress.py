import threading
import time
from unittest.mock import Mock
import pytest
from src.utils.progress import progress_reporter,progress_range,report_progress
from src.utils.spotify_compat import add_items
from src.utils.playlist_names import resolve_playlist_names,playlist_label
from src.gui.async_tasks import run_job


def test_nested_progress_maps_to_overall_job_and_restores_after_error():
    updates=[]
    with progress_reporter(lambda *args:updates.append(args)):
        with pytest.raises(ValueError):
            with progress_range(2,3,5,'Podcast → Mi lista'):
                report_progress(50,100,'Episodios agregados')
                raise ValueError('failed')
        report_progress(3,5,'Siguiente asignación')
    assert updates==[(2.5,5,'Podcast → Mi lista · Episodios agregados'),(3,5,'Siguiente asignación')]


def test_batch_progress_only_counts_successful_writes():
    sp=Mock()
    sp._get_uri.side_effect=lambda kind,uri:uri
    sp._post.side_effect=[{'snapshot_id':'one'},RuntimeError('failed')]
    updates=[]
    with progress_reporter(lambda *args:updates.append(args)):
        with pytest.raises(RuntimeError):add_items(sp,'playlist',['spotify:track:'+str(i) for i in range(205)])
    assert max(done for done,_,_ in updates)==100
    assert all(total==205 for _,total,_ in updates)


def test_names_use_catalog_and_only_query_each_missing_playlist_once():
    sp=Mock()
    sp.playlist.return_value={'name':'Podcast favoritos'}
    names=resolve_playlist_names(sp,['one','two','two'],known={'one':'Mi música'})
    assert names=={'one':'Mi música','two':'Podcast favoritos'}
    sp.playlist.assert_called_once_with('two',fields='name')
    assert playlist_label('one',names,saved='Nombre anterior')=='Mi música'


def test_unavailable_playlist_uses_saved_name_without_losing_its_id():
    sp=Mock()
    sp.playlist.side_effect=RuntimeError('403')
    names=resolve_playlist_names(sp,['private'],known={})
    assert playlist_label('private',names,'Mi lista privada')=='Mi lista privada'
    assert playlist_label('deleted',names)=='Playlist no disponible (deleted)'


class FakeRoot:
    def __init__(self):
        self.callbacks=[]
        self.alive=True
        self.finished=0
        self.progress=[]
    def winfo_toplevel(self):return self
    def winfo_exists(self):return self.alive
    def after(self,_,callback):self.callbacks.append(callback)
    def job_started(self):pass
    def job_finished(self):self.finished+=1
    def job_progress(self,*args):self.progress.append((threading.get_ident(),args))


@pytest.mark.parametrize('alive',[True,False])
def test_worker_progress_is_delivered_on_main_thread_and_ignores_closed_frame(alive):
    root=FakeRoot()
    callbacks=[]
    worker_done=threading.Event()
    main_thread=threading.get_ident()
    def work():
        assert threading.get_ident()!=main_thread
        report_progress(1,2,'Primera playlist')
        worker_done.set()
        return 'done'
    run_job(root,work,lambda value:callbacks.append(('success',value)),
            on_progress=lambda *args:callbacks.append((threading.get_ident(),args)))
    assert worker_done.wait(2)
    root.alive=alive
    deadline=time.monotonic()+2
    while root.callbacks and time.monotonic()<deadline:
        root.callbacks.pop(0)()
        if not root.finished:time.sleep(.001)
    assert root.finished==1
    assert all(thread_id==main_thread for thread_id,_ in root.progress)
    if alive:
        assert callbacks[-1]==('success','done')
        assert any(item[0]==main_thread for item in callbacks)
    else:
        assert not callbacks
