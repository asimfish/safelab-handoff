"""Bind runtime task context without modifying trained configuration on disk."""
def bind_executor_context(executor,global_task):
 if not isinstance(global_task,str) or not global_task.strip():raise ValueError('nonempty runtime global_task required')
 task=global_task.strip();config=executor._agent.config
 previous=config.get('global_task')
 if previous is not None and previous!=task:raise ValueError('runtime task context differs from already-bound task')
 from omegaconf import OmegaConf
 before=OmegaConf.to_container(config,resolve=False)
 OmegaConf.update(config,'global_task',task,force_add=True)
 after=OmegaConf.to_container(config,resolve=False);expected=dict(before,global_task=task)
 if after!=expected:raise RuntimeError('unexpected configuration change beyond runtime global_task')
 return {'runtime_global_task_bound':True,'field_added':previous is None,'trained_config_file_modified':False,'changed_fields':['global_task']if previous is None else[]}

def bind_policy_context(policy,global_task):
 receipt=bind_executor_context(policy.executor,global_task)
 original=policy.reset
 def reset(*,global_task=None):
  task=policy.global_task if global_task is None else global_task
  bind_executor_context(policy.executor,task)
  return original(global_task=task)
 policy.reset=reset
 return receipt

def create_policy_from_delivery(delivery,*,global_task,**kwargs):
 """Use the delivered factory and bind the same task into its executor context."""
 from pathlib import Path
 if not isinstance(global_task,str)or not global_task.strip():raise ValueError('nonempty runtime global_task required')
 small=Path('/project_a02012413/public/liyufeng').resolve()
 for name in ['audit_dir','runtime_dir']:
  if kwargs.get(name)is None or not Path(kwargs[name]).expanduser().resolve().is_relative_to(small):raise ValueError(f'{name} must be explicit and within the authorized small-file root')
 policy=delivery.create_policy(global_task=global_task.strip(),**kwargs)
 policy._runtime_context_binding=bind_policy_context(policy,global_task.strip())
 return policy
