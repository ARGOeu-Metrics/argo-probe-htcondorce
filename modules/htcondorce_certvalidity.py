import datetime
import os
import re
import signal
import subprocess
import sys

import OpenSSL
import htcondor
import pytz
from argo_probe_htcondorce.probe_response import ProbeResponse
from dateutil.parser import parse


class TimeoutException(Exception):
    pass


class timeout:
    def __init__(self, seconds=1, error_message="Timeout"):
        self.seconds = seconds
        self.error_message = error_message

    def handle_timeout(self, signum, frame):
        raise TimeoutException(self.error_message)

    def __enter__(self):
        signal.signal(signal.SIGALRM, self.handle_timeout)
        signal.alarm(self.seconds)

    def __exit__(self, exc_type, exc_val, exc_tb):
        signal.alarm(0)


def validate_certificate(args):
    status = ProbeResponse()

    # Setting X509_USER_PROXY environmental variable
    os.environ["X509_USER_PROXY"] = args.user_proxy

    try:
        ad = htcondor.Collector(f"{args.hostname}:9619").locate(
            htcondor.DaemonTypes.Schedd, args.hostname
        )
        cert = htcondor.SecMan().ping(ad, "READ")["ServerPublicCert"]
        x509 = OpenSSL.crypto.load_certificate(
            OpenSSL.crypto.FILETYPE_PEM, cert
        )
        expiration_date = parse(x509.get_notAfter())

        subject = x509.get_subject()
        cn = subject.CN
        pattern = re.compile(cn.replace('*', '[A-Za-z0-9_-]+?'))
        cn_ok = False
        if bool(re.match(pattern, args.hostname)):
            cn_ok = True

        else:
            ext_count = x509.get_extension_count()
            san = ''
            for i in range(ext_count):
                ext = x509.get_extension(i)
                if 'subjectAltName' in str(ext.get_short_name()):
                    san = ext.__str__()

            if san:
                for alt_name in san:
                    pattern = re.compile(
                        alt_name.replace('*', '[A-Za-z0-9_-]+?')
                    )
                    if bool(re.match(pattern, args.hostname)):
                        cn_ok = True
                        break

        pem_filename = f"/tmp/{args.hostname}.pem"
        with open(pem_filename, 'w') as f:
            for line in cert:
                f.write(line)

        cmd = [
            'openssl', 'verify', '-verbose', '-CAfile', args.ca_bundle,
            pem_filename
        ]
        p = subprocess.Popen(
            cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        p.communicate()[0].decode('utf-8').strip()
        if os.path.isfile(pem_filename):
            os.remove(pem_filename)

        if p.returncode == 0:
            ca_ok = True

        else:
            ca_ok = False

        if cn_ok and ca_ok:
            if x509.has_expired():
                status.critical(
                    f"HTCondorCE certificate expired (was valid until "
                    f"{expiration_date.strftime('%b %-d %H:%M:%S %Y %Z')})!"
                )

            else:
                timedelta = expiration_date - datetime.datetime.now(tz=pytz.utc)

                if timedelta.days < 30:
                    status.warning(
                        f"HTCondorCE certificate will expire in "
                        f"{timedelta.days} day(s) on "
                        f"{expiration_date.strftime('%b %-d %H:%M:%S %Y %Z')}!"
                    )

                else:
                    status.ok(
                        f"HTCondorCE certificate valid until "
                        f"{expiration_date.strftime('%b %-d %H:%M:%S %Y %Z')} "
                        f"(expires in {timedelta.days} days)"
                    )

        else:
            if not cn_ok:
                status.critical(
                    f'invalid CN ({args.hostname} does not match {cn})'
                )

            else:
                status.critical('invalid CA chain')

    except htcondor.HTCondorException as e:
        status.unknown(f"Unable to fetch certificate: {str(e)}")

    except Exception as e:
        status.unknown(str(e))

    print(status.msg())
    sys.exit(status.code())
