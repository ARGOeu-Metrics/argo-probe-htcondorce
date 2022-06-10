# argo-probe-htcondorce

The package contains probe `htcondorce-cert-check` which is checking the HTCondorCE certificate validity. In addition to certificate expiration date, the probe is also checking the CN. The probe returns WARNING if the certificate is due to expire in 30 days, and it returns CRITICAL if it is expired.

## Synopsis

The probe has several arguments; it requires user proxy, ca bundle, hostname and timeout.

```
# /usr/libexec/argo/probes/htcondorce/htcondorce-cert-check --help
usage: htcondorce-cert-check [-h] --user_proxy USER_PROXY -H HOSTNAME
                             [-t TIMEOUT] --ca-bundle CA_BUNDLE

Nagios probe for checking HTCondorCE certificate validity

optional arguments:
  -h, --help            show this help message and exit
  --user_proxy USER_PROXY
                        path to X509 user proxy
  -H HOSTNAME, --hostname HOSTNAME
                        hostname
  -t TIMEOUT, --timeout TIMEOUT
                        timeout
  --ca-bundle CA_BUNDLE
                        location of CA bundle
```

Example probe execution:

```
/usr/libexec/argo/probes/htcondorce/htcondorce-cert-check -H "htc.argo.grnet.gr" -t 60 --user_proxy /etc/nagios/globus/userproxy.pem-ops --ca-bundle /etc/pki/tls/certs/ca-bundle.crt
OK - HTCondorCE certificate valid until May 12 23:59:59 2023 UTC (expires in 336 days)
```
