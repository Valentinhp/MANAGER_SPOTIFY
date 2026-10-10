from unittest.mock import Mock,patch
import threading
import pytest
from spotipy.exceptions import SpotifyException
from src.utils.spotify_compat import search_paginated,create_playlist,read_items,add_items,remove_items,cached_entities,remove_from_library
from src.utils.api_decorator import handle_spotify_errors,SpotifyAccessError
from src.gui.ai_fusion import balanced_merge

def test_search_pages_are_at_most_ten():
    sp=Mock()
    sp.search.side_effect=[{'tracks':{'items':list(range(10)),'next':'next'}},{'tracks':{'items':list(range(10,20)),'next':'next'}},{'tracks':{'items':[20,21],'next':None}}]
    assert search_paginated(sp,'test','track',22)['tracks']['items']==list(range(22))
    assert [(call.kwargs['offset'],call.kwargs['limit']) for call in sp.search.call_args_list]==[(0,10),(10,10),(20,2)]

def test_new_playlist_paths_and_item_response():
    sp=Mock()
    sp._get_uri.side_effect=lambda uri,kind:uri
    create_playlist(sp,'Test',False,'Description')
    sp._post.assert_called_with('me/playlists',payload={'name':'Test','public':False,'description':'Description'})
    sp._get.return_value={'items':[{'item':{'id':'track'}}],'next':None}
    assert read_items(sp,'p',fields='items(track(id)),next')['items'][0]['track']['id']=='track'
    sp._get.assert_called_with('playlists/p/items',limit=50,offset=0,additional_types='track,episode',fields='items(item(id)),next')
    add_items(sp,'p',[f'spotify:track:{i}' for i in range(205)])
    assert [len(call.kwargs['payload']['uris']) for call in sp._post.call_args_list[1:]]==[100,100,5]
    remove_items(sp,'p',[{'uri':'spotify:track:t'}])
    sp._delete.assert_called_with('playlists/p/items',payload={'items':[{'uri':'spotify:track:t'}]})
    remove_from_library(sp,['spotify:playlist:p'])
    sp._delete.assert_called_with('me/library',uris='spotify:playlist:p')

def test_entity_cache_avoids_bulk_and_copy_mutation():
    sp=Mock();sp.track.return_value={'id':'abc','name':'Original'}
    with patch('src.utils.spotify_compat.time.sleep'):
        cached_entities(sp,'track',['abc'])['tracks'][0]['name']='Changed'
        assert cached_entities(sp,'track',['abc'])['tracks'][0]['name']=='Original'
    sp.track.assert_called_once_with('abc');sp.tracks.assert_not_called()

def test_403_is_readable_and_not_swallowed():
    @handle_spotify_errors()
    def fail():raise SpotifyException(403,-1,'Forbidden')
    with pytest.raises(SpotifyAccessError,match='Premium'):fail()

def test_429_waits_on_worker_and_retries():
    operation=Mock(side_effect=[SpotifyException(429,-1,'limited',headers={'Retry-After':'2'}),'ok'])
    @handle_spotify_errors()
    def wrapped():
        return operation()
    output=[]
    with patch('src.utils.api_decorator.time.sleep') as sleep:
        thread=threading.Thread(target=lambda:output.append(wrapped()))
        thread.start();thread.join(timeout=3)
        assert output==['ok'];sleep.assert_called_once_with(2)

def test_balanced_merge_keeps_order_and_removes_duplicates():
    def song(i):return {'id':str(i),'uri':f'spotify:track:{i}'}
    assert [t['id'] for t in balanced_merge([song(1),song(2),song(3)],[song(4),song(1)])]==['1','4','2','3']
