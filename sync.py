#!/usr/bin/env python3
# Storage‑sync TUI — minutes (m), hours (h), days (d) • clear (x) • sync (s)

from blessed import Terminal
import os, json, argparse
from datetime import datetime, timedelta
from contextlib import nullcontext
from dotenv import load_dotenv
from label_studio_sdk.client import LabelStudio
from crontab import CronTab          # pip install python-crontab

CONFIG_FILE = 'storage_config.json'

# ────────────────────────────── env & SDK ────────────────────────────────────
load_dotenv()
LABEL_STUDIO_URL = os.getenv('LABEL_STUDIO_URL')
API_KEY          = os.getenv('API_KEY')
ls   = LabelStudio(base_url=LABEL_STUDIO_URL, api_key=API_KEY)
term = Terminal()

# ─────────────────────────── support functions ───────────────────────────────
def maybe_hide_cursor(t):             # safe hidden_cursor for all terms
    h = t.hidden_cursor()
    return h if hasattr(h, '__enter__') else nullcontext()

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE) as f: return json.load(f)
        except json.JSONDecodeError:
            print(f'⚠️  Corrupt {CONFIG_FILE}; starting fresh.')
    return []

def save_config(storages):
    with open(CONFIG_FILE, 'w') as f: json.dump(storages, f, indent=2)

# ───────────────────────── cron job management ───────────────────────────────
def update_cron_jobs(storages):
    cron = CronTab(user=True)
    cron.remove_all(comment='storage_sync_job')
    script_path = os.path.abspath(__file__)

    for i, s in enumerate(storages):
        if s['update_frequency'] is None: continue
        job = cron.new(command=f'python {script_path} --sync {i+1}',
                       comment='storage_sync_job')
        if s['frequency_unit'] == 'minutes':
            job.minute.every(s['update_frequency'])
        elif s['frequency_unit'] == 'hours':
            job.hour.every(s['update_frequency'])
        else:                                   # days
            job.day.every(s['update_frequency'])
            job.hour.on(0); job.minute.on(0)
    cron.write()

# ───────────────────────── collect storage list ──────────────────────────────
def get_all_storages():
    saved = {f"{s.get('project_id')}_{s.get('storage_id')}": s
             for s in load_config()}
    result=[]
    for proj in ls.projects.list():
        for st in ls.export_storage.gcs.list(project=proj.id):
            key=f"{proj.id}_{st.id}"
            rec=dict(project_id=proj.id, project_name=proj.title,
                     storage_id=st.id, storage_title=st.title,
                     update_frequency=None, frequency_unit=None,
                     last_synced=None, next_sync=None)
            if key in saved: rec.update(saved[key])
            result.append(rec)
    return result

# ────────────────────────────── UI drawing ───────────────────────────────────
def display_storages(storages, sel=0, msg=''):
    print(term.clear)
    print(term.bold_white_on_blue(term.center('=== EXPORT STORAGES ===')))
    print(term.bold('ID | Project | Storage | Freq | Last Sync | Next Sync'))
    print(term.bold('-'*term.width))
    for i,s in enumerate(storages,1):
        freq=(f"{s['update_frequency']} {s['frequency_unit']}"
               if s['update_frequency'] else 'Not set')
        line=(f"{i} | {s['project_name']} | {s['storage_title']} | "
              f"{freq:<14} | {s['last_synced'] or 'Never':<16} | "
              f"{s['next_sync'] or 'N/A'}")
        print(term.black_on_white(line) if i-1==sel else line)
    print(term.bold('-'*term.width))
    opts=("↑/↓ Navigate | Enter Select | s Sync | c Configure | "
          "x Clear | q Quit")
    print(term.bold_white_on_blue(term.center(opts)))
    if msg:
        print(term.move(term.height-2,0)+term.clear_eol+
              term.bold_yellow(f"Status: {msg}"))

# ────────────────────────────── actions ──────────────────────────────────────
def sync_storage(idx, storages):
    s=storages[idx]
    try:
        ls.export_storage.gcs.sync(id=s['storage_id'])
        now=datetime.now(); s['last_synced']=now.strftime('%Y-%m-%d %H:%M')
        if s['update_frequency']:
            delta = (timedelta(minutes=s['update_frequency'])
                     if s['frequency_unit']=='minutes' else
                     timedelta(hours =s['update_frequency'])
                     if s['frequency_unit']=='hours' else
                     timedelta(days  =s['update_frequency']))
            s['next_sync']=(now+delta).strftime('%Y-%m-%d %H:%M')
        save_config(storages); return 'Sync OK'
    except Exception as exc:
        return f'Error: {exc}'

def configure_storage(idx, storages):
    # unit prompt
    print(term.move(term.height-5,0)+term.clear_eos)
    print(term.bold('Unit (m=minutes, h=hours, d=days): '),end='',flush=True)
    unit=''
    while unit not in ('m','h','d'):
        unit=str(term.inkey()).lower()
    print(unit)

    # number prompt
    print(term.bold('Frequency number: '),end='',flush=True)
    num=''
    while True:
        k=term.inkey()
        if str(k).isdigit():
            num+=str(k); print(k,end='',flush=True)
        elif k.name=='KEY_ENTER': break
    if not num: return 'Cancelled.'
    num=int(num)
    lim=120 if unit=='m' else 24 if unit=='h' else 10
    if not 1<=num<=lim: return f'Invalid (1–{lim})'

    s=storages[idx]
    s.update(update_frequency=num,
             frequency_unit=('minutes' if unit=='m'
                             else 'hours'  if unit=='h'
                             else 'days'))
    now=datetime.now()
    s['last_synced']=now.strftime('%Y-%m-%d %H:%M')
    delta=(timedelta(minutes=num) if unit=='m' else
           timedelta(hours  =num) if unit=='h' else
           timedelta(days   =num))
    s['next_sync']=(now+delta).strftime('%Y-%m-%d %H:%M')
    save_config(storages); update_cron_jobs(storages)
    return 'Frequency updated.'

def clear_schedule(idx, storages):
    s=storages[idx]
    if s['update_frequency'] is None: return 'No schedule to clear.'
    s.update(update_frequency=None,frequency_unit=None,next_sync=None)
    save_config(storages); update_cron_jobs(storages)
    return 'Schedule cleared.'

# ─────────────────────────── interactive loop ────────────────────────────────
def tui_loop(storages):
    sel,msg=0,''
    with term.fullscreen(),term.cbreak(),maybe_hide_cursor(term):
        while True:
            display_storages(storages,sel,msg)
            k=term.inkey()
            if k.name=='KEY_UP'   and sel:                       sel-=1
            elif k.name=='KEY_DOWN'and sel<len(storages)-1:      sel+=1
            elif k.code in (term.KEY_ENTER,term.KEY_RETURN) or k=='\n':
                msg=f"Selected {storages[sel]['storage_title']}"
            elif str(k).lower()=='s':
                msg='Syncing…'; display_storages(storages,sel,msg)
                msg=sync_storage(sel,storages)
            elif str(k).lower()=='c':
                msg=configure_storage(sel,storages)
            elif str(k).lower()=='x':
                msg=clear_schedule(sel,storages)
            elif str(k).lower()=='q':
                break

# ───────────────────────────── entrypoint ────────────────────────────────────
def main():
    ap=argparse.ArgumentParser(description='Storage Sync TUI')
    ap.add_argument('--sync',type=int,help='Sync storage by ID then exit')
    args=ap.parse_args()

    storages=get_all_storages()
    if args.sync:
        print(sync_storage(args.sync-1,storages)); return
    tui_loop(storages)
    print(term.normal+term.clear+'Bye!')

if __name__=='__main__':
    main()
