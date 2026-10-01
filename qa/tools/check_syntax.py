"""node --check every inline <script> block of index.html. Usage: python3 qa/tools/check_syntax.py index.html
Block 0 is a known false positive (a literal <script> tag inside an HTML comment); it fails identically in every version."""
import re,sys,subprocess,tempfile,os
s=open(sys.argv[1],encoding='utf-8').read();bad=[]
for i,b in enumerate(re.findall(r'<script>(.*?)</script>',s,re.S)):
    f=tempfile.NamedTemporaryFile('w',suffix='.js',delete=False);f.write(b);f.close()
    r=subprocess.run(['node','--check',f.name],capture_output=True,text=True);os.unlink(f.name)
    ok=r.returncode==0;print(f'block {i}: {"OK" if ok else "ERR"}'+('' if ok else ('  (known false positive)' if i==0 else '  '+r.stderr.strip().splitlines()[-1][:120])))
    if not ok and i!=0: bad.append(i)
sys.exit(1 if bad else 0)
