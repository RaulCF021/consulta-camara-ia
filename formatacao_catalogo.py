"""Formatação determinística de registros normalizados da API."""
LABELS={'nomeCivil':'Nome civil','escolaridade':'Escolaridade','sexo':'Sexo cadastral','municipioNascimento':'Município de nascimento','ufNascimento':'UF de nascimento','dataNascimento':'Nascimento','ultimoStatus':'Último registro cadastral','siglaPartido':'Partido','siglaUf':'UF','siglaUF':'UF','nome':'Nome','titulo':'Título','dataHora':'Data','descricaoSituacao':'Situação','descricaoTramitacao':'Tramitação','siglaOrgao':'Órgão','dataInicio':'Início','dataFim':'Fim','situacao':'Situação','statusProposicao':'Situação da proposta','dataApresentacao':'Apresentação','tipo':'Tipo','proponente':'Proponente (indicador oficial)','ordemAssinatura':'Ordem de assinatura','dataHoraInicio':'Início','dataHoraFim':'Fim','despacho':'Despacho','orientacaoVoto':'Orientação de voto','siglaPartidoBloco':'Partido/bloco','ementa':'Ementa','ultimoStatus_descricaoSituacao':'Situação'}
HIDE={'uri','uriPartido','uriOrgao','uriEvento','urlRegistro','urlWebsite','urlInteiroTeor','url','codTipoProfissao','codTitulo','id','idLegislatura'}

def lines(value,prefix='',depth=0):
    if isinstance(value,dict):
        out=[]
        for k,v in value.items():
            if k in HIDE or k.lower().startswith(('uri','url','cod')) or v in (None,'',[],{}):continue
            label=LABELS.get(k,k)
            if isinstance(v,(dict,list)):
                out.append(prefix+label+':');out.extend(lines(v,prefix+'  ',depth+1))
            else:out.append(prefix+label+': '+str(v))
        return out
    if isinstance(value,list):return [line for v in value[:20] for line in lines(v,prefix,depth+1)]
    return [prefix+str(value)]

def format_catalog(data):
    target=data.get('alvo') or {}
    result=data['titulo']+(f" — {target['rotulo']}" if target.get('rotulo') else '')
    filters=data.get('filtros_executados',{})
    if filters.get('dataInicio') or filters.get('dataFim'):result+='\nPeríodo enviado à fonte: '+filters.get('dataInicio','início não definido')+' a '+filters.get('dataFim','fim não definido')+'.'
    if not data['itens']:result+='\nA fonte não retornou registros para esse recorte. Isso não comprova inexistência fora da cobertura consultada.'
    for n,item in enumerate(data['itens'],1):
        text='\n'.join(lines(item)) or 'Registro sem campos descritivos.'
        result+=f'\n\n{n}. '+text
    total=data['total_encontrado'];shown=data['exibidos']
    result+=f'\n\nExibindo {shown} de {total} registros obtidos.'
    if not data['cobertura_completa']:result+=' Cobertura parcial: '+data.get('observacao','')
    if shown<total:result+=' A lista exibida é uma amostra; peça outra quantidade (até 20).'
    if data['recurso']=='evento_participantes':result+=' Participação registrada no evento não equivale à frequência integral em plenário.'
    if data['recurso']=='proposta_detalhes':result+=' A situação transcrita é o registro oficial da proposição; não implica, sozinha, aprovação em todas as etapas ou vigência de uma lei.'
    if data.get('referencias'):result+='\nVocê pode selecionar um item pela posição e pedir seus detalhes.'
    if data.get('recurso_pendente'):
        from capacidades import CAPABILITIES
        result+='\nPara consultar '+CAPABILITIES[data['recurso_pendente']]['label'].lower()+', selecione um dos itens apresentados.'
    return result
