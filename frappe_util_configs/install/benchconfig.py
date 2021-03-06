import frappe, click, os
import frappe_util_configs

def update_config():
  change_cwd_to_bench()
  update_supervisor()
  update_procfile()
  change_cwd_to_bench(revert=True)
  click.echo("You may have to restart bench to complete configuration")

def change_cwd_to_bench(revert=False):
  # frappe commands are executed at frappe-bench/sites dir
  # Changing this to just frappe-bench
  os.chdir(os.path.join(os.getcwd(), "sites" if revert else ".."))

def update_supervisor():
  # Update supervisor iff ./config/supervisor.conf exists only
  supervisor_filepath = os.path.join('.', 'config', 'supervisor.conf')
  if not os.path.exists(supervisor_filepath):
    click.echo("Supervisor config not found")
    return
  
  with open(supervisor_filepath, 'r+') as f:
    supervisor_config = f.read().strip()
    
    if not supervisor_config:
      frappe.throw("Invalid supervisor config file")
  
    supervisor_config = supervisor_config.replace("frappe.app:application", "frappe_util_configs.app:application")
    supervisor_config = supervisor_config.replace("apps/frappe/socketio.js", "apps/frappe_util_configs/socketio.js")

    f.seek(0)
    f.write(supervisor_config)

  click.echo("Supervisor config file updated to use frappe_util_configs.app.application and frappe_util_configs/socketio.js")

def update_procfile():
  # Update supervisor iff ./config/supervisor.conf exists only
  procfile_path = os.path.join('.', 'Procfile')
  if not os.path.exists(procfile_path):
    click.echo("Procfile not found")
    return
  
  with open(procfile_path, 'r+') as f:
    proc = f.read().strip()
  
    if not proc:
      frappe.throw("Invalid procfile")

    proc = proc.replace("apps/frappe/socketio.js", "apps/frappe_util_configs/socketio.js")
    f.seek(0)
    f.write(proc)
  
  click.echo("Procfile updated to use frappe_util_configs/socketio.js")