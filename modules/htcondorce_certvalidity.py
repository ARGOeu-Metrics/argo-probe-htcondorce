import datetime
import os
import re
import signal
import subprocess
import sys
import time

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


class Certificate:
    def __init__(self, args):
        self.hostname = args.hostname
        self.ca_bundle = args.ca_bundle
        self.status = ProbeResponse()
        self.pem_filename = f"/tmp/{self.hostname}.pem"

        # Setting X509_USER_PROXY environmental variable
        os.environ["X509_USER_PROXY"] = args.user_proxy

    def _htcondor_fetch(self):
        ad = htcondor.Collector(f"{self.hostname}:9619").locate(
            htcondor.DaemonTypes.Schedd, self.hostname
        )

        return htcondor.SecMan().ping(ad, "READ")["ServerPublicCert"]

    def _fetch(self):
        try:
            cert = self._htcondor_fetch()

            if not cert:
                time.sleep(30)

                cert = self._htcondor_fetch()

            self._save(cert)

            return cert

        except htcondor.HTCondorException:
            raise

    def _is_cn_ok(self, x509):
        subject = x509.get_subject()
        cn = subject.CN
        pattern = re.compile(cn.replace('*', '[A-Za-z0-9_-]+?'))
        cn_ok = False
        if bool(re.match(pattern, self.hostname)):
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
                    if bool(re.match(pattern, self.hostname)):
                        cn_ok = True
                        break

        return cn_ok

    def _is_ca_ok(self):
        cmd = [
            'openssl', 'verify', '-verbose', '-CAfile', self.ca_bundle,
            self.pem_filename
        ]
        p = subprocess.Popen(
            cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        p.communicate()[0].decode('utf-8').strip()

        if p.returncode == 0:
            ca_ok = True

        else:
            ca_ok = False

        return ca_ok

    def _save(self, cert):
        with open(self.pem_filename, 'w') as f:
            for line in cert:
                f.write(line)

    def _clear(self):
        if os.path.isfile(self.pem_filename):
            os.remove(self.pem_filename)

    def _check_expiration(self, x509):
        expiration_date = parse(x509.get_notAfter())
        if x509.has_expired():
            self.status.critical(
                f"HTCondorCE certificate expired (was valid until "
                f"{expiration_date.strftime('%b %-d %H:%M:%S %Y %Z')})!"
            )

        else:
            timedelta = expiration_date - datetime.datetime.now(tz=pytz.utc)

            if timedelta.days < 30:
                self.status.warning(
                    f"HTCondorCE certificate will expire in "
                    f"{timedelta.days} day(s) on "
                    f"{expiration_date.strftime('%b %-d %H:%M:%S %Y %Z')}!"
                )

            else:
                self.status.ok(
                    f"HTCondorCE certificate valid until "
                    f"{expiration_date.strftime('%b %-d %H:%M:%S %Y %Z')} "
                    f"(expires in {timedelta.days} days)"
                )

    def validate(self):
        try:
            cert = self._fetch()

            if cert:
                x509 = OpenSSL.crypto.load_certificate(
                    OpenSSL.crypto.FILETYPE_PEM, cert
                )

                subject = x509.get_subject()
                cn = subject.CN

                cn_ok = self._is_cn_ok(x509)

                ca_ok = self._is_ca_ok()

                if cn_ok and ca_ok:
                    self._check_expiration(x509)

                else:
                    if not cn_ok:
                        self.status.critical(
                            f'invalid CN ({self.hostname} does not match {cn})'
                        )

                    else:
                        self.status.critical('invalid CA chain')

        except htcondor.HTCondorException as e:
            self.status.unknown(f"Unable to fetch certificate: {str(e)}")

        except Exception as e:
            self.status.unknown(str(e))

        self._clear()
        print(self.status.msg())
        sys.exit(self.status.code())
