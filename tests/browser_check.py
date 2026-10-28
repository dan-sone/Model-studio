"""Optional browser integration. Test-only inference fixtures; no live AI claim."""
import os
import tempfile
import threading
from http.server import ThreadingHTTPServer
from unittest.mock import patch
from playwright.sync_api import sync_playwright, expect
from model_studio.server import make_handler
from model_studio.store import Store
from test_chain import initial, proposal, op, node, relation


def main():
    with tempfile.TemporaryDirectory() as tmp:
        store=Store(tmp+'/browser.sqlite3')
        server=ThreadingHTTPServer(('127.0.0.1',0),make_handler(store,''))
        worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
        branch=proposal([op(node('credit','decision','Godkänd kredit?')),op(node('stop',label='Avslag')),op(relation('yes','credit','pick',label='Ja'),target='relation'),op(relation('no','credit','stop',label='Nej'),target='relation')])
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'),args=['--no-sandbox'])
                page=browser.new_page(viewport={'width':1440,'height':1000})
                errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
                page.goto('http://127.0.0.1:'+str(server.server_port))
                expect(page.locator('#status')).to_contain_text('AI är inte konfigurerad')
                expect(page.locator('#send')).to_be_disabled()
                with patch('model_studio.provider.configured',return_value=True),patch('model_studio.provider.infer',side_effect=[initial(),branch,proposal(kind='clarification',message='Vilken kontroll menar du?')]):
                    page.locator('#reload').click()
                    expect(page.locator('#send')).to_be_enabled()
                    page.locator('#message').fill('Skapa en Order to Cash-process med Microsoft Dynamics 365 F&O som system.')
                    page.locator('#send').click()
                    expect(page.locator('#version')).to_have_text('Version 1')
                    expect(page.locator('#diagram svg')).to_be_visible()
                    page.locator('#message').fill('Lägg in kreditkontroll och en separat väg när kunden inte blir godkänd.')
                    page.locator('#send').click()
                    expect(page.locator('#version')).to_have_text('Version 2')
                    expect(page.locator('#diagram polygon')).to_have_count(1)
                    expect(page.locator('#diagram text').filter(has_text='Nej')).to_have_count(1)
                    page.locator('#message').fill('Flytta kontrollen')
                    page.locator('#send').click()
                    expect(page.locator('#messages')).to_contain_text('Vilken kontroll menar du?')
                    expect(page.locator('#version')).to_have_text('Version 2')
                    page.screenshot(path='/tmp/model-studio-desktop.png',full_page=True)
                    # A fresh device-sized browser reads the same server workspace.
                    mobile=browser.new_page(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
                    mobile.goto('http://127.0.0.1:'+str(server.server_port))
                    expect(mobile.locator('#version')).to_have_text('Version 2')
                    assert mobile.evaluate('document.documentElement.scrollWidth <= innerWidth')
                    mobile.screenshot(path='/tmp/model-studio-mobile.png',full_page=True)
                    page.locator('#undo').click()
                    expect(page.locator('#version')).to_have_text('Version 3')
                    expect(page.locator('#diagram polygon')).to_have_count(0)
                    page.reload();expect(page.locator('#version')).to_have_text('Version 3')
                assert not errors,errors
                browser.close()
                print('Browser OK: unconfigured, creation, branching, clarification, persistence, undo, desktop and mobile. Inference fixtures only.')
        finally:
            server.shutdown();server.server_close();worker.join()


if __name__=='__main__':main()
