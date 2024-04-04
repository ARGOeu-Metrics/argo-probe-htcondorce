%define underscore() %(echo %1 | sed 's/-/_/g')

Name: argo-probe-htcondorce
Summary: ARGO probe checking HTCondorCE certificate validity.
Version: 0.2.0
Release: 1%{?dist}
License: ASL 2.0
Source0: %{name}-%{version}.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root
Group: Network/Monitoring
BuildArch: noarch

BuildRequires: python3-devel

%if 0%{?el7}
Requires: python36-requests
Requires: python36-pyOpenSSL
Requires: python36-pytz
Requires: python36-dateutil

%else
Requires: python3-requests
Requires: python3-pyOpenSSL
Requires: python3-pytz
Requires: python3-dateutil

%endif


%description
This package includes probe that checks HTCondorCE certificate validity.


%prep
%setup -q


%build
%{py3_build}


%install
%{py3_install "--record=INSTALLED_FILES" }


%clean
rm -rf $RPM_BUILD_ROOT


%files -f INSTALLED_FILES
%defattr(-,root,root)
%dir %{python3_sitelib}/%{underscore %{name}}/
%{python3_sitelib}/%{underscore %{name}}/*.py


%changelog
* Thu Apr 4 2024 Katarina Zailac <kzailac@srce.hr> - 0.1.0-1%{?dist}
- ARGO-4496 HTCondorCE certificate validity probe raising weird CRITICAL error on Sensu
- ARGO-4481 Rewrite htcondorce certificate validity probe to use Py3
* Fri Jun 10 2022 Katarina Zailac <kzailac@gmail.com> - 0.1.0-1%{?dist}
- AO-650 Harmonize argo-mon probes
