{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = [
    pkgs.python311
    pkgs.python311Packages.pip
    pkgs.python311Packages.gunicorn
    pkgs.python311Packages.flask
    pkgs.python311Packages.pandas
    pkgs.python311Packages.pdf2image
    pkgs.python311Packages.python-pptx
    pkgs.python311Packages.cryptography
  ];
  
  shellHook = ''
    export FLASK_ENV=production
    export PYTHONUNBUFFERED=1
    pip install -r requirements.txt
  '';
}
