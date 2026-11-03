import copy,math,struct,unittest,io,json
from pathlib import Path
from unittest.mock import patch
import portable_placement as entry
p=entry.oracle
DT=struct.unpack('<f',struct.pack('<f',1/120))[0]
def initial():
 def obj(x,pad):return {'link_position_world_m':[x,0,.05],'tilt_deg':0,'robot_contact_points':0,'hand_contact_points':0,'support_contact_points':{pad:1},'bottom_world_z_m':0}
 return {'tick':0,'native_tick':0,'sim_time_s':0.,'actual_physics_elapsed_s':0.,'objects':{'A':obj(0,'rack_S1'),'B':obj(.2,'rack_S2')},'supports':{'rack_S1':{'center_world_m':[0,0,0]},'rack_S2':{'center_world_m':[.2,0,0]},'operation_tray':{'center_world_m':[.4,0,0]}},'liquid_counts':{'total':200,'A':200,'B':0,'outside_vessels':0,'in_transit':0,'currently_spilled_outside':0,'spill':0},'native_contacts_observable':True,'all17_native_hand2_links_covered':True,'whole_episode_task_actions_written_by_observer':False,'safety_violation':False,'native_report_min_separation_m':0.}
def row(i,poured=False):
 r=initial();r.update(tick=i,native_tick=i,sim_time_s=i/120,actual_physics_elapsed_s=i*DT)
 if poured:r['liquid_counts'].update(A=0,B=200)
 return r
def fixture(lose_final=False):
 out=[]
 for i in range(641):
  r=row(i,i>=362);a=r['objects']['A'];a['object_pose_in_wrist']={'position_m':[0,0,0],'quaternion_wxyz':[1,0,0,0]}
  if 1<=i<=602:
   a.update(hand_contact_points=1,robot_contact_points=1,bottom_world_z_m=.07,support_contact_points={});a['link_position_world_m']=[0,0,.12]
  if 362<=i<=602:a['tilt_deg']=45;a['link_position_world_m']=[.2,0,.12]
  if lose_final and i==640:a['link_position_world_m'][0]=.021
  contacts=[]
  for key in ['A','B']:
   o=r['objects'][key];o['support_contact_points']={k:o['support_contact_points'].get(k,0)for k in r['supports']}
   other='/World/envs/env_0/Robot/hand2_thumb' if o['hand_contact_points'] else '/World/envs/env_0/Support_'+('rack_S1' if key=='A' else 'rack_S2')
   contacts.append({'count':1,'actor0':'/World/envs/env_0/Bottle'+key,'collider0':'/World/envs/env_0/Bottle'+key+'/shape','actor1':other,'collider1':other+'/shape','minimum_separation_m':0.})
  r['native_contacts']=contacts;out.append(r)
 return out
def synthetic_rescore(rows):
 real=Path.open;raw=('\n'.join(json.dumps(r)for r in rows)+'\n').encode()
 def op(path,*a,**k):return io.BytesIO(raw) if path.name=='synthetic_fixture.jsonl' else real(path,*a,**k)
 with patch.object(Path,'open',op):return p.rescore('synthetic_fixture.jsonl',len(rows))

class Cases(unittest.TestCase):
 def test_start_on_pad_never_completes(self):
  c=p.compile_oracle()['OrderedPhysics'](initial())
  for i in range(1,121):c.consume(row(i))
  self.assertEqual(c.phase,0)
 def test_exact_30_intervals_and_no_speed_fields(self):
  c=p.compile_oracle()['OrderedPhysics'](initial());c.phase=2
  for i in range(1,31):c.consume(row(i,True))
  self.assertEqual(c.phase,2);c.consume(row(31,True));self.assertEqual(c.phase,3)
 def test_held_on_pad_rejected(self):
  r=row(1,True);r['objects']['A'].update(robot_contact_points=1,hand_contact_points=1);self.assertFalse(p.placement(r,'A','rack_S1'))
 def test_airborne_over_target_rejected(self):
  r=row(1,True);r['objects']['A'].update(support_contact_points={},bottom_world_z_m=.006);self.assertFalse(p.placement(r,'A','rack_S1'))
 def test_outside_region_rejected(self):
  r=row(1,True);r['objects']['A']['link_position_world_m'][0]=.02001;self.assertFalse(p.placement(r,'A','rack_S1'))
 def test_tilt_rejected(self):
  r=row(1,True);r['objects']['A']['tilt_deg']=15;self.assertFalse(p.placement(r,'A','rack_S1'))
 def test_debounce_resets_after_contact(self):
  c=p.compile_oracle()['OrderedPhysics'](initial());c.phase=2
  for i in range(1,21):c.consume(row(i,True))
  r=row(21,True);r['objects']['A']['robot_contact_points']=1;c.consume(r)
  for i in range(22,52):c.consume(row(i,True))
  self.assertEqual(c.phase,2);c.consume(row(52,True));self.assertEqual(c.phase,3)
 def test_full_sequence_without_velocity_threshold(self):
  a=synthetic_rescore(fixture());self.assertTrue(a['success']);self.assertEqual(a['physical_phase'],3)
 def test_final_placement_loss_fails_whole_episode(self):
  a=synthetic_rescore(fixture(True));self.assertFalse(a['success']);self.assertEqual(a['physical_phase'],3);self.assertEqual(a['error'],'final_placement_not_retained')
if __name__=='__main__':unittest.main()
