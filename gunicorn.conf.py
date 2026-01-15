# Gunicorn configuration file otimizado para Render
# ================================================

import multiprocessing
import os

# Bind
bind = f"0.0.0.0:{os.getenv('PORT', '5000')}"

# Workers - FIXO em 1 para manter dados em memória consistentes (sem MySQL)
workers = 1
worker_class = os.getenv('GUNICORN_WORKER_CLASS', 'sync')  # 'gevent' se instalar gevent

# Threads por worker (para sync workers)
threads = int(os.getenv('GUNICORN_THREADS', '4'))

# Timeout - aumentar para evitar timeout em cold start
timeout = 120
graceful_timeout = 30
keepalive = 5

# Preload app - IMPORTANTE: reduz tempo de cold start
# Carrega a aplicação antes de fazer fork dos workers
preload_app = True

# Max requests - recicla workers para evitar memory leaks
max_requests = 1000
max_requests_jitter = 50

# Logging
accesslog = '-'
errorlog = '-'
loglevel = os.getenv('LOG_LEVEL', 'warning')  # Menos logs = mais rápido
access_log_format = '%(h)s %(l)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" %(L)ss'

# Performance
worker_tmp_dir = '/dev/shm'  # Usar memória RAM para arquivos temporários (mais rápido)

# Callback quando worker é iniciado
def on_starting(server):
    """Chamado quando Gunicorn inicia"""
    pass

def post_fork(server, worker):
    """Chamado após fork de cada worker"""
    # Reconectar ao banco se necessário
    pass

def pre_request(worker, req):
    """Chamado antes de cada request"""
    pass
