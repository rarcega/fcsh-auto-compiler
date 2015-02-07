#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
Usage: 
python app.py [--config <config_path>, --properties <properties_path>]
'''
import os, sys, time, logging, subprocess, threading, socket, shlex, yaml, argparse
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from watchdog.utils.dirsnapshot import DirectorySnapshot, DirectorySnapshotDiff
from dirtools import Dir

logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s [%(levelname)s] - %(message)s',
                        datefmt='%I:%M:%S')
LOG = logging.getLogger(__name__)

class ChangeHandler(FileSystemEventHandler):
  def __init__(self, runtime, path):
    self.runtime = runtime
    self.ref = Dir(path).hash()
    self.ref_snapshot = DirectorySnapshot(path, recursive=True)
    self.path = path
    
  def on_any_event(self, event):
    LOG.debug('%s %s', event.event_type, event.src_path)
    
    new_ref = Dir(self.path).hash()
    snapshot = DirectorySnapshot(self.path, recursive=True)
    diff     = DirectorySnapshotDiff(self.ref_snapshot, snapshot)
        
    # compare directory hashes to determine if recompile needed
    if self.ref != new_ref:
      self.print_changes(diff)
      self.runtime.compile()
      self.ref = new_ref
      self.ref_snapshot = snapshot
      
  def print_changes(self, diff):
    if diff.files_created:
      LOG.info('Created:')
      [ LOG.info('\t' + str(file)) for file in diff.files_created ]
        
    if diff.files_modified:
      LOG.info('Modified:')
      [ LOG.info('\t' + str(file)) for file in diff.files_modified ]
        
    if diff.files_moved:
      LOG.info('Moved:')
      [ LOG.info('\t' + str(file)) for file in diff.files_moved ]
      
    if diff.files_deleted:
      LOG.info('Deleted:')
      [ LOG.info('\t' + str(file)) for file in diff.files_deleted ]
 
 
class BuildWorker(threading.Thread):
  def __init__(self, prj):
    threading.Thread.__init__(self)
    self.kill_received = False
    self.port = str(get_open_port())
    self.project = prj
    self.compile_proc = None
    self.observers = []
    
    for src_path in self.project['src_paths']:
      if os.path.exists( src_path['path'] ):
        self.observers.append(Observer())
        self.observers[-1].schedule(ChangeHandler(self, src_path['path']), path=src_path['path'], recursive=src_path['recursive'])
        self.observers[-1].start()
      else:
        LOG.warn('Source path "%s" could not be found, skipping monitoring.' % src_path['path'])
      
    if len(self.observers) > 0:
      LOG.info('Waiting for changes in %s...', self.project['name'])
    else:
      LOG.error("No valid source paths exist for %s. Can't build project." % self.project['name'])
            
  def run(self):
    while not self.kill_received:
      pass
    
    self.stop_compile()
    
    for observer in self.observers:
      observer.stop()
      observer.join()
  
  def compile(self):
    LOG.info('Building %s... (socket=:%s)', self.project['name'], self.port)
    start_time = time.time()
    
    if isinstance(self.project['compile_command'], basestring):
        self.compile_proc = subprocess.Popen(shlex.split('python flexcompile.py -p ' + self.port + ' -c "' + self.project['compile_command'] + '"'))
        self.compile_proc.communicate()
    else:
        for cmd in self.project['compile_command']:
            self.compile_proc = subprocess.Popen(shlex.split('python flexcompile.py -p ' + self.port + ' -c "' + cmd + '"'))
            self.compile_proc.communicate()

    duration = time.time() - start_time
    LOG.info('Finished %s in %s seconds.', self.project['name'], (round(duration, 2)))
    LOG.info('Waiting for changes in %s...', self.project['name'])
    
  def stop_compile(self):
    if self.compile_proc is not None and self.compile_proc.poll() is None:
        self.compile_proc.terminate() # or .kill() if it doesn't terminate it
        self.compile_proc.communicate() # close pipes, wait for completion
        self.compile_proc = None

        
def get_open_port():
  s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  s.bind(('',0))
  s.listen(1)
  port = s.getsockname()[1]
  s.close()
  return port
  
def load_config():
    props = dict(line.strip().split('=', 1) for line in open('config.properties'))
    with open('config.yaml', 'r') as file:
        contents = file.read()
        
    for property, value in props.iteritems():
      contents = contents.replace('{{' + property + '}}', value) 
      
    return yaml.load(contents)
    
def main(argv):
  config = load_config()

  threads = []
  
  for prj in config['projects']:
    if prj['enabled']:
        t = BuildWorker(prj)
        t.daemon = True
        threads.append(t)
        t.start()

  while True:
    try:
      # Join all threads using a timeout so it doesn't block
      # Filter out threads which have been joined or are None
      threads = [t.join(1000) for t in threads if t is not None and t.isAlive()]
    except KeyboardInterrupt:
      for t in threads:
        t.kill_received = True
        
        # Kill the fcsh daemon
        p = subprocess.Popen(shlex.split('python flexcompile.py --kill-daemon -p ' + t.port))
        p.communicate()
      
      sys.exit(0)
      
if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument('-p', '--properties', default='config.properties', help='config property file for variable interpolation')
  parser.add_argument('-c', '--config', default='config.yaml', help='application config file')
  args = parser.parse_args()
    
  main(args)  