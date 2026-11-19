"""Configure a chave no computador que executa o serviço."""
from getpass import getpass
from modelos import KEY_FILE
import os
if __name__=="__main__":
    value=getpass("Chave da API OpenAI (entrada oculta): ").strip()
    if not value:raise SystemExit("Nenhuma chave alterada.")
    KEY_FILE.parent.mkdir(parents=True,exist_ok=True)
    KEY_FILE.write_text(value,encoding="utf8")
    if os.name!="nt":KEY_FILE.chmod(0o600)
    print("Chave salva na configuração local do usuário. O serviço passa a usá-la na próxima pergunta.")
