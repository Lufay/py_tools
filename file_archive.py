import asyncio
from pathlib import Path
import hashlib
from enum import Enum, auto
import pickle
import heapq
from collections import UserString
from pprint import pprint
import shutil

class FileOp(Enum):
    SHOW=auto()
    DEL=auto()

def mv_file_out(path:str):
    '''若指定路径下的文件夹只有一个文件，且与文件夹同名，则将文件移出来，并删除文件夹
    '''
    p = Path(path)
    for d in p.iterdir():
        if d.is_dir():
            for i, f in enumerate(d.iterdir()):
                if i > 0:
                    break
            else:
                if d.name == f.stem:
                    f.replace(d.parent/f.name)
                    d.rmdir()

class LongestMinStr(UserString):
    def __gt__(self, string: str | UserString) -> bool:
        return super().__lt__(string)

    def __lt__(self, string: str | UserString) -> bool:
        return super().__gt__(string)
    
    def __ge__(self, string: str | UserString) -> bool:
        return super().__le__(string)

    def __le__(self, string: str | UserString) -> bool:
        return super().__ge__(string)

class FileMd5:
    same_file_suffix = '的副本'
    def __init__(self, file:str) -> None:
        self.updated = False
        self.file = Path(file)
        self.file_md5 = {}
        self.basename_md5names:dict[str, tuple[set, list]] = {}
        parent = self.file.parent
        if parent.exists():
            if self.file.is_file():
                with open(file, 'rb') as f:
                    file_md5:dict = pickle.load(f)
            else:
                file_md5 = {}
                self.updated = True
            for f in parent.iterdir():
                if f != self.file and not f.name.startswith('.'):
                    if (fname := f.name) in file_md5:
                        self.load_file(f, file_md5[fname])
                    else:
                        self.load_file(f)
        else:
            print(f'{parent} is not a file!')

    @classmethod
    def get_base_name(cls, name:str) -> tuple[str, int]:
        suffix = cls.same_file_suffix
        while name.endswith(suffix):
            name = name.removesuffix(suffix)
        return name
    
    def load_file(self, file:str|Path, md5=None):
        '''
        file 已更新或新移入，需要加载md5
        '''
        if isinstance(file, str):
            file = Path(file)
        if file.parent == self.file.parent:
            if not md5:
                md5 = hashlib.md5(file.read_bytes()).hexdigest()
            self.file_md5[file.name] = md5
            self.updated = True
            base_name = self.get_base_name(file.stem) + file.suffix
            if base_name in self.basename_md5names:
                md5set, names = self.basename_md5names[base_name]
                md5set.add(md5)
                heapq.heappush(names, LongestMinStr(file.stem))
            else:
                self.basename_md5names[base_name] = {md5}, [LongestMinStr(file.stem)]
        else:
            print(f'{file} not in {self.file.parent}!')

    def move_in(self, file:Path, new_file_name, md5=None):
        try:
            new_file = file.replace(self.file.parent/new_file_name)
        except OSError:
            new_file = shutil.move(file, self.file.parent)
        self.load_file(new_file, md5)

    def sync_file(self):
        if self.updated:
            with open(self.file, 'wb') as f:
                pickle.dump(self.file_md5, f)

    def walk_dir(self, path:str, name:str):
        '''
        若已保存name，则递归遍历路径下，指定name 文件，若md5 相同则删除，否则则展示并移动重命名
        若未保存，则先移动保存后再遍历路径
        '''
        p = Path(path)
        if name in self.file_md5:
            base_name = self.get_base_name(name)
            md5set, names = self.basename_md5names[base_name]
            print(f'{name}-md5={md5set}')
            for file in p.rglob(name):
                md5 = hashlib.md5(file.read_bytes()).hexdigest()
                if md5 in md5set:
                    file.unlink()
                else:
                    print(f'{file}-md5={md5}')
                    new_file = file.with_stem(f'{names[0]}{self.same_file_suffix}')
                    self.move_in(file, new_file.name, md5)
        else:
            try:
                file = next(p.rglob(name))
                self.move_in(file, name)
                self.walk_dir(path, name)
            except StopIteration:
                print(f'{name} not in {path}')

async def get_input(default_path=None):
    while True:
        p = input('path: ')
        if not p and default_path:
            p = default_path
        path = Path(p)
        if path.is_dir():
            name = input('name: ').strip()
            if name.startswith(':'):
                name = name[1:].strip()
                if name == 'all':
                    gen = path.iterdir()
                elif name.startswith('p'):
                    gen = path.rglob(name[1:])
                else:
                    print(f'bad command {name}')
                    break
                for f in gen:
                    if f.is_file() and not f.name.startswith('.') and input(f'{f} y/n:') != 'n':
                        yield path, f.name
            else:
                yield path, None if set(name) & set('*?') else name
            default_path = p
        elif path.is_file():
            yield path.parent, path.name
            default_path = path.parent
        else:
            print(f'{p} not exists')
            break

async def producer(q: asyncio.Queue):
    async for pn in get_input():
        q.put_nowait(pn)
        await asyncio.sleep(0)

async def worker(fm:FileMd5, q: asyncio.Queue):
    while True:
        p, name = await q.get()
        if name:
            await asyncio.to_thread(fm.walk_dir, p, name)
        else:
            await asyncio.to_thread(mv_file_out, p)
        q.task_done()

async def main(fm:FileMd5, worker_num:int=5):
    q = asyncio.Queue()
    task_producer = asyncio.create_task(producer(q))
    task_workers = [asyncio.create_task(worker(fm, q))
                    for i in range(worker_num)]
    while not task_producer.done():
        await asyncio.sleep(1)
    await q.join()
    for task in task_workers:
        task.cancel()
    await asyncio.gather(task_producer, *task_workers, return_exceptions=True)
    
if __name__ == '__main__':
    fm = FileMd5('/Volumes/TOSHIBA EXT/杂项/pickle')
    pprint(fm.file_md5)
    pprint(fm.basename_md5names)
    try:
        asyncio.run(main(fm))
    except KeyboardInterrupt as e:
        print(f'ki: {e.args}')
    finally:
        fm.sync_file()