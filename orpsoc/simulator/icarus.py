import os
import shutil
import subprocess
from .simulator import Simulator

class SimulatorIcarus(Simulator):

    def __init__(self, system):
        super(SimulatorIcarus, self).__init__(system)
        self.sim_root = os.path.join(self.build_root, 'sim-icarus')

    def write_config_files(self):
        icarus_file = 'icarus.scr'

        f = open(os.path.join(self.sim_root,icarus_file),'w')

        for include_dir in self.include_dirs:
            f.write("+incdir+" + include_dir + '\n')
        for rtl_file in self.rtl_files:
            f.write(rtl_file + '\n')
        for tb_file in self.tb_files:
            f.write(tb_file + '\n')

        f.close()
    def compile(self):
        #FIXME: Handle failures. Save stdout/stderr. Build vmem file from elf file argument
        for name, core in self.system.get_cores().items():
            if core.vpi:
                core_root = os.path.join(self.build_root, 'src', name)
                print("Building VPI module for " + name)
                inc_dirs  = ['-I' + os.path.join(core_root, d) for d in core.vpi.include_dirs]
                src_files = [os.path.join(core_root, f) for f in core.vpi.src_files]

                if subprocess.call(['iverilog-vpi', '--name='+core.vpi.name] +
                                   inc_dirs +
                                   src_files,
                                   stderr = open(os.path.join(self.sim_root,name+'.log'),'w'),
                                   cwd = os.path.join(self.sim_root)):
                    print("Error: VPI compilation failed. The log is saved as "+os.path.join(self.sim_root, name+'.log'))
                    exit(1)
                                    
        if subprocess.call(['iverilog',
                            '-s', 'orpsoc_tb',
                            '-c', 'icarus.scr',
                            '-o', 'orpsoc.elf'],
                           cwd = os.path.join(self.build_root, 'sim-icarus')):
            print("Error: Compiled failed")
            exit(1)
        
    def run(self, args):
        vmem_file=os.path.abspath(args.testcase[0])
        if not os.path.exists(vmem_file):
            print("Error: Couldn't find test case " + vmem_file)
            exit(1)
        plusargs = ['+testcase='+vmem_file]
        if args.timeout:
            print("Setting timeout to "+str(args.timeout[0]))
            plusargs += ['+timeout='+str(args.timeout[0])]

        if args.enable_dbg:
            print("Enabling debug interface")
            plusargs += ['+enable_dbg']

        vpi_modules = []
        for name, core in self.system.get_cores().items():
            if core.vpi:
                vpi_modules += ['-m'+core.vpi.name]

        #FIXME: Handle failures. Save stdout/stderr. Build vmem file from elf file argument
        shutil.copyfile(vmem_file, os.path.join(self.build_root, 'sim-icarus', 'sram.vmem'))
        if subprocess.call(['vvp', '-n', '-M.',
                            '-l', 'icarus.log'] +
                           vpi_modules +
                           ['orpsoc.elf'] +
                           plusargs,
                           cwd = os.path.join(self.build_root, 'sim-icarus'),
                           stdin=subprocess.PIPE):
            print("Error: Failed to run simulation")

