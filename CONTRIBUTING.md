# Guia de Contribuição - Transcriber

Obrigado pelo seu interesse em contribuir com o **Transcriber**! 🎉

Este é um projeto Open Source focado em oferecer uma experiência simples, rápida e privada para transcrição de áudios e vídeos.

---

## 🛠️ Como Começar

### 1. Clonar o repositório
```bash
git clone https://github.com/realkalashnikov/transcriber.git
cd transcriber
```

### 2. Configurar o ambiente virtual
```bash
python -m venv .venv
# No Windows:
.venv\Scripts\activate
# No Linux/macOS:
source .venv/bin/activate
```

### 3. Instalar dependências
```bash
pip install -r requirements.txt
```

### 4. Rodar o servidor localmente
```bash
python run.py
```
Acesse `http://localhost:8000`.

---

## 🧪 Executando Testes

Antes de submeter um Pull Request, certifique-se de que todos os testes passem:

```bash
python test_app.py
```

---

## 📐 Padrões de Código

- Utilize **Conventional Commits**:
  - `feat(...)`: nova funcionalidade
  - `fix(...)`: correção de bug
  - `docs(...)`: documentação
  - `refactor(...)`: refatoração sem alteração de funcionalidade
  - `ci(...)`: ajustes no pipeline de CI/CD
- Mantenha o frontend livre de dependências pesadas de compilação (Node.js/npm) para garantir que qualquer usuário possa rodar com apenas Python.
- Sempre utilize ícones SVG vetoriais do módulo `icons.js` em vez de emojis soltos no HTML.

---

## 📬 Como Enviar seu Pull Request

1. Crie uma branch para sua funcionalidade: `git checkout -b minha-feature`
2. Faça seus commits: `git commit -m "feat: minha feature"`
3. Envie para o GitHub: `git push origin minha-feature`
4. Abra um **Pull Request** no GitHub detalhando suas alterações.
