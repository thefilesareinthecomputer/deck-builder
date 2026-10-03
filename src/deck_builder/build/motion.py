"""`build:`: the parts of one slide fade in, one click at a time.

PowerPoint's own Fade entrance, half a second, in reading order, and nothing else: no transition between
slides, no motion path, no fly-in. The engine writes the slide's `p:timing`; LibreOffice, the PDF and render QA
show the finished slide, and `import` reads a build it wrote back as `build:`.
"""
from __future__ import annotations

from typing import Any

from pptx.oxml import parse_xml
from pptx.oxml.ns import nsdecls, qn

FADE_MS = 500
Step = list[tuple[Any, int | None]]  # the shapes (and paragraph, for one item of a list) that appear on one click


def shape_id(el: Any) -> str:
    """The id of a shape element: p:sp, p:pic or p:graphicFrame all keep it in their first child's p:cNvPr."""
    return str(el[0].find(qn("p:cNvPr")).get("id"))


def _target(spid: str, para: int | None) -> str:
    text = "" if para is None else f'<p:txEl><p:pRg st="{para}" end="{para}"/></p:txEl>'
    return f'<p:tgtEl><p:spTgt spid="{spid}">{text}</p:spTgt></p:tgtEl>'


def _fade(ids: list[int], spid: str, para: int | None, node: str) -> str:
    """One Fade entrance: make the shape (or paragraph) visible, then fade it in."""
    a, b, c = ids.pop(0), ids.pop(0), ids.pop(0)
    tgt = _target(spid, para)
    return (f'<p:par><p:cTn id="{a}" presetID="10" presetClass="entr" presetSubtype="0" fill="hold" grpId="0" '
            f'nodeType="{node}"><p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>'
            f'<p:set><p:cBhvr><p:cTn id="{b}" dur="1" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst>'
            f'</p:cTn>{tgt}<p:attrNameLst><p:attrName>style.visibility</p:attrName></p:attrNameLst></p:cBhvr>'
            '<p:to><p:strVal val="visible"/></p:to></p:set>'
            f'<p:animEffect transition="in" filter="fade"><p:cBhvr><p:cTn id="{c}" dur="{FADE_MS}"/>{tgt}</p:cBhvr>'
            "</p:animEffect></p:childTnLst></p:cTn></p:par>")


def add_fade(slide: Any, steps: list[Step]) -> None:
    """Write the slide's timing: one click per step, the step's first shape as the click effect and the rest
    appearing with it. Ids count up from 3 (1 is the root, 2 the main sequence), so the XML is byte-stable."""
    ids = list(range(3, 3 + 5 * sum(len(s) for s in steps) + 2 * len(steps)))
    clicks = []
    for step in steps:
        outer, inner = ids.pop(0), ids.pop(0)
        effects = "".join(_fade(ids, shape_id(el), para, "clickEffect" if i == 0 else "withEffect")
                          for i, (el, para) in enumerate(step))
        clicks.append(f'<p:par><p:cTn id="{outer}" fill="hold"><p:stCondLst><p:cond delay="indefinite"/>'
                      f'</p:stCondLst><p:childTnLst><p:par><p:cTn id="{inner}" fill="hold"><p:stCondLst>'
                      f'<p:cond delay="0"/></p:stCondLst><p:childTnLst>{effects}</p:childTnLst></p:cTn></p:par>'
                      "</p:childTnLst></p:cTn></p:par>")
    builds: dict[str, str] = {}
    for step in steps:
        for el, para in step:
            spid = shape_id(el)
            if el.tag == qn("p:graphicFrame"):
                builds[spid] = f'<p:bldGraphic spid="{spid}" grpId="0"><p:bldAsOne/></p:bldGraphic>'
            elif el.tag == qn("p:sp"):
                builds[spid] = (f'<p:bldP spid="{spid}" grpId="0" build="p"/>' if para is not None
                                else f'<p:bldP spid="{spid}" grpId="0" animBg="1"/>')
    timing = parse_xml(
        f'<p:timing {nsdecls("p")}><p:tnLst><p:par><p:cTn id="1" dur="indefinite" restart="never" '
        'nodeType="tmRoot"><p:childTnLst><p:seq concurrent="1" nextAc="seek"><p:cTn id="2" dur="indefinite" '
        f'nodeType="mainSeq"><p:childTnLst>{"".join(clicks)}</p:childTnLst></p:cTn><p:prevCondLst><p:cond '
        'evt="onPrev" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:prevCondLst><p:nextCondLst><p:cond '
        'evt="onNext" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:nextCondLst></p:seq></p:childTnLst>'
        f'</p:cTn></p:par></p:tnLst>{"<p:bldLst>" + "".join(builds.values()) + "</p:bldLst>" if builds else ""}'
        "</p:timing>")
    sld = slide._element
    anchor = sld.find(qn("p:clrMapOvr"))
    if anchor is None:
        anchor = sld.find(qn("p:cSld"))
    anchor.addnext(timing)  # p:timing follows p:clrMapOvr (and any p:transition, which the engine never writes)
