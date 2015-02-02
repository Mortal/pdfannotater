import os
import tempfile
import subprocess
import PyPDF2


def compile_tex(sources):
    box_tex = r"""
    \setbox0=\hbox{%%
    %% \begin{minipage}{%%(width/stretch)gbp}%%
    %% \fontsize{%%(fontsize)g}{%%(fontsize * 6 / 5)dbp}\selectfont
    %% %%(fontsize_string)s
    \ipesetcolor
    %% minipage style???
    %(element)s%%
    \iperesetcolor}
    \count0=\dp0%%
    \divide\count0 by \bigpoint
    \pdfxform attr{/IpeId %(ipeid)s /IpeDepth \the\count0}0%%
    \pdfrefxform\pdflastxform
    """.strip()

    boxes = [box_tex % dict(element=source, stretch=1, ipeid=i)
             for i, source in enumerate(sources)]

    tex = r"""\pdfcompresslevel0
    \nonstopmode
    \documentclass{article}
    \newcommand{\PageTitle}[1]{#1}
    \newdimen\ipefs
    \newcommand{\ipesymbol}[4]{\ipefs 1ex\pdfliteral{(#1) (\the\ipefs) (#2) (#3) (#4) sym}}
    \usepackage{color}
    \definecolor{black}{gray}{0}
    \definecolor{red}{rgb}{1,0,0}
    \def\ipesetcolor{\pdfcolorstack0 push{0 0 0 0 k 0 0 0 0 K}}
    \def\iperesetcolor{\pdfcolorstack0 pop}
    %(preamble)s%%
    \pagestyle{empty}
    \newcount\bigpoint\dimen0=0.01bp\bigpoint=\dimen0
    \begin{document}
    %(boxes)s%%
    \hbox{}
    \end{document}
    """ % dict(
        preamble='',
        boxes=''.join(boxes),
    )
    with tempfile.NamedTemporaryFile('w', prefix='pdfannotator', suffix='.tex', delete=False) as fp:
        fp.write(tex)
        fp.close()
        proc = subprocess.Popen(
            ('pdflatex', fp.name),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            cwd=os.path.dirname(fp.name))
        stdoutdata, stderrdata = proc.communicate()
        returncode = proc.wait()
        if returncode != 0 or stderrdata:
            print(stdoutdata)
            print(stderrdata)  # Should be empty
            raise SystemExit('pdflatex returned exit status %d' % returncode)
        return fp.name.replace('.tex', '.pdf')


def main():
    filename = compile_tex(['Hello worlg!', r'$\sum_{i=1}^\infty 1/i$'])
    fp = open(filename, 'rb')
    pdf = PyPDF2.PdfFileReader(fp)
    page1 = pdf.getPage(0)
    print(page1['/Contents'])
    print(page1['/Contents']._data)
    res = page1['/Resources']
    obj = res['/XObject']
    for xform_key, xform_ref in obj.items():
        print("xform_key = %r" % (xform_key,))
        xform = xform_ref.getObject()
        for k, v in xform.items():
            print("%r: %r" % (k, v))
        print(xform._data)
        ipeid = xform['/IpeId']
        depth = xform['/IpeDepth']
        bbox = xform['/BBox']
        x0, y0, width, height = bbox
        print(bbox)
        res = xform['/Resources']
        fontdict = xform.get('/Font')
    # for page in pdf.pages:
    #     for k, v in page.items():
    #         print("%r: %r," % (k.getObject(), v.getObject()))
    #     print(page['/Resources']


if __name__ == "__main__":
    main()
