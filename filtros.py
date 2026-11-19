"""Reconhecimento de valores explícitos dos filtros do catálogo."""
import csv,io,re
from functools import lru_cache
from fontes import read_text
STATES = dict(zip(
"AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO".split(),
["acre","alagoas","amapa","amazonas","bahia","ceara","distrito federal","espirito santo","goias","maranhao","mato grosso","mato grosso do sul","minas gerais","para","paraiba","parana","pernambuco","piaui","rio de janeiro","rio grande do norte","rio grande do sul","rondonia","roraima","santa catarina","sao paulo","sergipe","tocantins"]))
@lru_cache(maxsize=1)
def parties():
    raw=read_text("https://dadosabertos.camara.leg.br/arquivos/partidos/csv/partidos.csv")
    return {r["sigla"].casefold() for r in csv.DictReader(io.StringIO(raw.lstrip("\ufeff")),delimiter=";")}
def explicit_filters(text, previous):
    values={};spans=[]
    sexes=list(re.finditer(r"\b(homem|homens|masculin[oa]s?|mulher|mulheres|feminin[oa]s?)\b",text))
    if sexes:
        found={"M" if m[0].startswith(("hom","masc")) else "F" for m in sexes}
        if len(found)==1:values["sexo"]=found.pop();spans.extend((m.start(),m.end()) for m in sexes)
    # Longest names first prevent Mato Grosso from consuming Mato Grosso do Sul.
    occupied=set()
    for uf,name in sorted(STATES.items(),key=lambda kv:len(kv[1]),reverse=True):
        for m in re.finditer(r"\b"+re.escape(name)+r"\b",text):
            positions=set(range(m.start(),m.end()))
            if positions&occupied:continue
            values["uf"]=uf;spans.append((m.start(),m.end()));occupied|=positions
    for m in re.finditer(r"\b[a-z][a-z0-9-]{1,12}\b",text):
        token=m[0]
        if token in parties():
            if token=='pl':
                if re.match(r'\s*\d',text[m.end():]):continue
                explicit_party=bool(re.search(r'\b(?:partido|bancada)\s+(?:do\s+)?pl\b|\b(?:orientou|orientacao)\b',text))
                bill_context=bool(re.search(r'\b(?:expli\w*|resum\w*|ementa|conteudo|situacao|tramit\w*|assinad\w*)\b',text))
                party_relation=bool(re.search(r'\b(?:do|pelo|no)\s+pl\b',text))
                if not explicit_party and (bill_context or not party_relation):continue
            values["partido"]=token.upper();spans.append((m.start(),m.end()))
    remainder=list(text)
    for a,b in spans:remainder[a:b]=" "*(b-a)
    rest=re.sub(r"\b(e|entre|as|os|a|o|de|do|da|dos|das|no|na|em|agora|so|somente|apenas|tambem|com|por|favor)\b|[\s,.?!]","","".join(remainder))
    return values,bool(values and not rest)
