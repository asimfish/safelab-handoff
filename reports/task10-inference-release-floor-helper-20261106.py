"""Only hand-drive transition after physical joint release; never changes body pose."""
import numpy as np

class ReleaseTargetFloor:
    """Rebase opening onto measured grasp and prevent a closing snap on release.

    Local six-hand indices0..5 map to q13 indices7..12. Thumb base0 opens
    toward smaller angles; flexion1..4 open toward larger angles. Index5
    is restored smoothly without assigning an unverified opening direction.
    """
    def __init__(self,held,raw,tick,transition_ticks=8,closing_epsilon_rad=.03,raw_at_latch=None,opening_reference_rad=2.9):
        self.held=np.asarray(held,dtype=np.float32).copy()
        raw=np.asarray(raw,dtype=np.float32)
        assert self.held.shape==raw.shape==(6,) and np.isfinite(raw).all() and np.isfinite(self.held).all()
        assert transition_ticks==8 and closing_epsilon_rad==.03
        self.anchor=np.asarray(raw if raw_at_latch is None else raw_at_latch,dtype=np.float32).copy()
        assert self.anchor.shape==(6,) and np.isfinite(self.anchor).all() and opening_reference_rad==2.9
        self.open_reference=np.maximum(np.float32(opening_reference_rad),np.maximum(self.held,self.anchor))
        self.start_tick=int(tick);self.transition_ticks=transition_ticks;self.epsilon=closing_epsilon_rad
        self.finger_peak=float(raw[1:3].mean());self.thumb_min=float(raw[0])
        self.last=self.held.copy();self.mode='opening';self.close_origin=None;self.close_tick=None;self.done=False

    def apply(self,raw,tick):
        raw=np.asarray(raw,dtype=np.float32);assert raw.shape==(6,) and np.isfinite(raw).all()
        tick=int(tick);assert tick>=self.start_tick and not self.done
        mean=float(raw[1:3].mean());thumb=float(raw[0])
        self.finger_peak=max(self.finger_peak,mean);self.thumb_min=min(self.thumb_min,thumb)
        finger_closing=mean<self.finger_peak-self.epsilon
        thumb_closing=thumb>self.thumb_min+self.epsilon
        # Either established closing phase can end the floor; ignore sub30mrad jitter.
        if self.mode=='opening' and (finger_closing or thumb_closing):
            self.mode='closing_restore';self.close_origin=self.last.copy();self.close_tick=tick
        if self.mode=='closing_restore':
            alpha=np.float32(min(1.,(tick-self.close_tick)/self.transition_ticks))
            delivered=(np.float32(1.)-alpha)*self.close_origin+alpha*raw
            self.done=bool(alpha==1.)
        else:
            desired=raw.copy();desired[0]=min(float(raw[0]),float(self.held[0]))
            # Rebase the policy opening coordinate onto the measured held pose.
            # Meet the original absolute-open reference with zero remaining offset.
            for j in range(1,5):
                end=self.open_reference[j];begin=self.anchor[j]
                if raw[j]>=end or end<=begin:desired[j]=max(float(raw[j]),float(self.held[j]))
                else:
                    fraction=np.float32(np.clip((raw[j]-begin)/(end-begin),0.,1.))
                    desired[j]=self.held[j]+fraction*(end-self.held[j])
            alpha=np.float32(min(1.,(tick-self.start_tick)/self.transition_ticks))
            delivered=(np.float32(1.)-alpha)*self.held+alpha*desired
            fully_caught_up=raw[0]<=self.held[0] and bool(np.all(raw[1:5]>=self.open_reference[1:5]))
            self.done=bool(alpha==1. and fully_caught_up)
        self.last=delivered.astype(np.float32,copy=True)
        assert np.isfinite(self.last).all()
        return self.last.copy()
