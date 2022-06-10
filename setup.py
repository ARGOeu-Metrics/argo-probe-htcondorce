from distutils.core import setup
import glob
import sys

NAME = 'argo-probe-htcondorce'
NAGIOSPLUGINS = '/usr/libexec/argo/probes/htcondorce'


def get_ver():
    try:
        for line in open(NAME+'.spec'):
            if "Version:" in line:
                return line.split()[1]
    except IOError:
        print "Make sure that %s is in directory"  % (NAME+'.spec')
        sys.exit(1)


setup(name=NAME,
      version=get_ver(),
      license='ASL 2.0',
      author='SRCE, GRNET',
      author_email='kzailac@srce.hr',
      description='Package includes probe for checking HTCondorCE certificate '
                  'validity',
      platforms='noarch',
      url='http://argoeu.github.io/',
      data_files=[(NAGIOSPLUGINS, glob.glob('src/*'))],
      packages=['argo_probe_htcondorce'],
      package_dir={'argo_probe_htcondorce': 'modules/'},
      )
