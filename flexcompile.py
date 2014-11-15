#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Fork of https://code.google.com/p/flexcompile
'''
import os
import re
import time
import socket
import subprocess
import sys
import traceback
import logging
import argparse

logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s [%(levelname)s] - %(message)s',
                        datefmt='%I:%M:%S')
LOG = logging.getLogger(__name__)

HOST = socket.gethostname()

def slurp_chunk(proc, conn):
    chunk = ""
    while True:
        l = proc.stdout.read(1)
        if l is None:
            break
        conn.send(l)
        chunk += l
        if chunk.endswith("\n(fcsh)"):
            return chunk

def daemon(port):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
          s.bind((HOST, port))
        except socket.error as msg:
          LOG.error('Bind failed. Error Code : ' + str(msg[0]) + ' Message ' + msg[1])
        s.listen(5)
        curdir = os.getcwd()
        cmd = ""
        proc = None
        prevcmds = {}
        while True:
            conn, addr = s.accept()
            LOG.debug('Connected with ' + addr[0] + ':' + str(addr[1]))
            data = conn.recv(1024) 
            if data == 'kill':
              LOG.info('Closing socket ' + str(s.getsockname()))
              conn.close()
              s.close()
              if proc: proc.kill()  
              break
            needkill = False
            for line in data.split("&&"):
                line = line.strip()
                LOG.debug("< %s" % line)
                if line.startswith("cd "):
                    d = line[3:].strip()
                    if d != curdir:
                        curdir = d
                        needkill = True
                else:
                    cmd = line
                    if cmd in prevcmds:
                        cmd = "compile %d" % prevcmds[cmd]
            if not proc or needkill:
                if proc:
                    proc.stdin.close()
                    proc.wait()
                os.chdir(curdir)
                LOG.debug("Starting fcsh process...")
                proc = subprocess.Popen(['fcsh'],
                                        stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT)
                chunk = slurp_chunk(proc, conn)

            LOG.debug("Writing %s" % cmd)
            proc.stdin.write(cmd + "\n")
            proc.stdin.flush()
            chunk = slurp_chunk(proc, conn)
            if cmd not in prevcmds:
                match = re.search(r'fcsh: Assigned (\d+) as the compile target id',
                                  chunk)
                if match:
                    prevcmds[cmd] = int(match.group(1))
            conn.send("\nDone\n")
            conn.close()
            time.sleep(1)
            LOG.debug("Closed connection")
    except:
      traceback.print_exc()
      if s: s.close()
      if proc: proc.kill()  

def run(cmd, port, start_daemon_if_missing=True):
    cmd = "cd %s && %s" % (os.getcwd(), cmd)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((HOST, port))
    except socket.error:
        if not start_daemon_if_missing:
            LOG.info("No daemon process; running directly.")
            os.system(cmd)
            return
        LOG.info("No daemon process, creating one...")
        os.system('start /B "" python %s --start-daemon --port %i --command "%s"' % (sys.argv[0], port, cmd))
        time.sleep(2)
        return run(cmd, port, start_daemon_if_missing=False)
    s.send(cmd)
    result = ""
    while True:
        data = s.recv(10240)
        sys.stdout.write(data)
        sys.stdout.flush()
        result += data
        if result.endswith("\nDone\n"):
            break
            
if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument("-c", "--command", help="mxmlc compilation command")
  parser.add_argument("-d", "--start-daemon", help="create fcsh daemon", action="store_true")
  parser.add_argument("-p", "--port", help="socket port", type=int, default=53000)
  parser.add_argument("-k", "--kill-daemon", help="kill the daemon process", action="store_true")
  args = parser.parse_args()
  
  if args.kill_daemon:
      s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      try:
          s.connect( (HOST, args.port) )
          s.send('kill')
      except socket.error:
         pass    
  elif args.start_daemon:
      daemon(args.port)
  else:
      try:
        run(args.command, args.port)
      except Exception, err:
        LOG.error(traceback.format_exc())