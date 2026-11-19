from avaliar_trajetorias import assess

def turn(clarify=False):return {'retorno':{'contexto':{'temas':['despesas']},'aguardando_esclarecimento':clarify}}
def test_trajectory_detects_wrong_or_repeated_tools():
    assert not assess(turn(),[{'event':'validation'},{'event':'tool','tool':'despesas','status':'ok'}])
    assert assess(turn(),[{'event':'validation'},{'event':'tool','tool':'projetos','status':'ok'}])
    assert assess(turn(),[{'event':'validation'},{'event':'tool','tool':'despesas'},{'event':'tool','tool':'despesas'}])
def test_trajectory_rejects_queries_before_clarification():
    assert not assess(turn(True),[{'event':'validation'},{'event':'clarification'}])
    assert assess(turn(True),[{'event':'validation'},{'event':'tool','tool':'despesas'}])

def test_entity_resolution_can_legitimately_ask_for_selection():
    t={'retorno':{'contexto':{'temas':['dados_legislativos'],'aguardando_selecao':True},'aguardando_esclarecimento':True}}
    assert not assess(t,[{'event':'validation'},{'event':'tool','tool':'dados_legislativos','status':'clarification'}])
    assert assess(t,[{'event':'validation'},{'event':'tool','tool':'despesas','status':'ok'}])
