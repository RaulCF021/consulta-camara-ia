"""Exporta o diagrama do mesmo grafo executável usado pela API."""
from pathlib import Path
from agente import build_graph
from ferramentas import CamaraTools

def export():
    diagram=build_graph(CamaraTools()).get_graph().draw_mermaid()
    target=Path(__file__).with_name('workflow.mmd')
    target.write_text(diagram+'\n',encoding='utf8')
    return target

if __name__=='__main__':
    print(export().name)
