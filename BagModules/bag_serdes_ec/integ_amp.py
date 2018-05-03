# -*- coding: utf-8 -*-

from typing import Dict, Any

import os
import pkg_resources

from bag.design import Module


yaml_file = pkg_resources.resource_filename(__name__, os.path.join('netlist_info',
                                                                   'integ_amp.yaml'))


# noinspection PyPep8Naming
class bag_serdes_ec__integ_amp(Module):
    """Module for library bag_serdes_ec cell integ_amp.

    Fill in high level description here.
    """

    def __init__(self, bag_config, parent=None, prj=None, **kwargs):
        Module.__init__(self, bag_config, yaml_file, parent=parent, prj=prj, **kwargs)

    @classmethod
    def get_params_info(cls):
        # type: () -> Dict[str, str]
        return dict(
            lch='channel length, in meters.',
            w_dict='NMOS/PMOS width dictionary.',
            th_dict='NMOS/PMOS threshold flavor dictionary.',
            seg_dict='number of segments dictionary.',
            flip_sign='True to flip output sign.',
            dum_info='Dummy information data structure.',
            export_probe='True to export probe ports.',
        )

    @classmethod
    def get_default_param_values(cls):
        # type: () -> Dict[str, Any]
        return dict(
            flip_sign=False,
            dum_info=None,
            export_probe=False,
        )

    def design(self, lch, w_dict, th_dict, seg_dict, flip_sign, dum_info, export_probe):
        seg_load = seg_dict.get('load', 0)
        seg_set = seg_dict.get('set', 0)
        seg_sen = seg_dict.get('sen', 0)
        seg_casc = seg_dict.get('casc', 0)
        seg_casc1 = seg_dict.get('but', 0)

        if seg_casc > 0 and seg_casc1 > 0:
            raise ValueError('Cannot have both cascode transistor and butterfly switch.')
        if seg_load > 0 and seg_casc1 > 0:
            raise ValueError('Cannot have both butterfly switch and load.')

        seg_casc0 = max(seg_casc, seg_casc1)
        tran_info_list = [('XTAILP', 'tail'), ('XTAILN', 'tail'),
                          ('XNENP', 'nen'), ('XNENN', 'nen'),
                          ('XINP', 'in'), ('XINN', 'in'),
                          ('XPENP0', 'pen'), ('XPENP1', 'pen'),
                          ('XPENN0', 'pen'), ('XPENN1', 'pen'),
                          ('XLOADP0', 'load'), ('XLOADP1', 'load'),
                          ('XLOADN0', 'load'), ('XLOADN1', 'load'),
                          ('XCASP0', 'casc', seg_casc0), ('XCASN0', 'casc', seg_casc0),
                          ('XCASP1', 'casc', seg_casc1), ('XCASN1', 'casc', seg_casc1),
                          ('XSETP', 'in', seg_set), ('XSETN', 'in', seg_set),
                          ('XSENP', 'nen', seg_sen), ('XSENN', 'nen', seg_sen),
                          ]

        outp_name, outn_name = ('outn', 'outp') if flip_sign else ('outp', 'outn')

        for inst_info in tran_info_list:
            if len(inst_info) <= 2:
                inst_name, inst_type = inst_info
                seg = seg_dict.get(inst_type, 0)
            else:
                inst_name, inst_type, seg = inst_info
            w = w_dict.get(inst_type, 0)
            th = th_dict.get(inst_type, 'standard')
            if seg <= 0:
                self.delete_instance(inst_name)
            else:
                self.instances[inst_name].design(w=w, l=lch, nf=seg, intent=th)

        if seg_casc1 > 0:
            if flip_sign:
                self.reconnect_instance_terminal('XCASP0', 'D', outp_name)
                self.reconnect_instance_terminal('XCASN0', 'D', outn_name)
                self.reconnect_instance_terminal('XCASP1', 'D', outn_name)
                self.reconnect_instance_terminal('XCASN1', 'D', outp_name)
        elif seg_casc > 0:
            self.rename_pin('casc<1:0>', 'casc')
            self.reconnect_instance_terminal('XCASP0', 'G', 'casc')
            self.reconnect_instance_terminal('XCASN0', 'G', 'casc')
            if flip_sign:
                self.reconnect_instance_terminal('XCASP0', 'D', outp_name)
                self.reconnect_instance_terminal('XCASN0', 'D', outn_name)
        else:
            for name in ('casc<1:0>', 'nmp', 'nmn'):
                self.remove_pin(name)
            self.reconnect_instance_terminal('XINP', 'D', outp_name)
            self.reconnect_instance_terminal('XINN', 'D', outn_name)

        if seg_load <= 0:
            for name in ('pm0p', 'pm0n', 'pm1p', 'pm1n', 'clkp', 'clkn'):
                self.remove_pin(name)
        elif flip_sign:
            self.reconnect_instance_terminal('XPENP0', 'D', outp_name)
            self.reconnect_instance_terminal('XPENP1', 'D', outp_name)
            self.reconnect_instance_terminal('XPENN0', 'D', outn_name)
            self.reconnect_instance_terminal('XPENN1', 'D', outn_name)

        if seg_set <= 0:
            for name in ('setp', 'setn', 'pulse', 'nsp', 'nsn'):
                self.remove_pin(name)
        elif flip_sign:
            self.reconnect_instance_terminal('XSETP', 'D', outp_name)
            self.reconnect_instance_terminal('XSETN', 'D', outn_name)

        self.design_dummy_transistors(dum_info, 'XDUM', 'VDD', 'VSS')
        if dum_info is not None:
            # delete intermediate ports
            for pin_name in ('pm0p', 'pm0n', 'pm1p', 'pm1n', 'tail', 'foot', 'nmp', 'nmn',
                             'nsp', 'nsn'):
                if not export_probe or (pin_name != 'tail' and pin_name != 'foot'):
                    self.remove_pin(pin_name)
