from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import json

app = Flask(__name__)
# Configura o SQLite (o arquivo database.db será criado na pasta)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


class Autor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    nascimento = db.Column(db.String(10)) 
    livros = db.relationship('Livro', backref='autor', lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'nascimento': self.nascimento,
            'livros_count': len(self.livros)
        }

class Livro(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    ano_publicacao = db.Column(db.Integer)
    isbn = db.Column(db.String(20), unique=True, nullable=False)
    autor_id = db.Column(db.Integer, db.ForeignKey('autor.id'), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'titulo': self.titulo,
            'ano_publicacao': self.ano_publicacao,
            'isbn': self.isbn,
            'autor_id': self.autor_id,
            'nome_autor': self.autor.nome
        }
        
@app.cli.command('init-db')
def init_db_command():
    """Comando para criar as tabelas do banco de dados (database.db)."""
    with app.app_context():
        db.create_all()
        print('Banco de dados e tabelas criados com sucesso!')

# =======================================================
# 4. ROTAS PARA AUTORES
# =======================================================

# Rota GET (Listar) e POST (Criar)
@app.route('/api/autores', methods=['GET', 'POST'])
def handle_autores():
    if request.method == 'GET':
        autores = Autor.query.all()
        return jsonify([autor.to_dict() for autor in autores])

    if request.method == 'POST':
        data = request.get_json()
        if not data or 'nome' not in data:
            return jsonify({'erro': 'Nome do autor é obrigatório.'}), 400

        novo_autor = Autor(nome=data['nome'], nascimento=data.get('nascimento'))
        db.session.add(novo_autor)
        db.session.commit()
        return jsonify(novo_autor.to_dict()), 201
    # =======================================================
# Rota GET/PUT/DELETE por ID
@app.route('/api/autores/<int:autor_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_autor(autor_id):
    autor = Autor.query.get_or_404(autor_id) 

    if request.method == 'GET':
        return jsonify(autor.to_dict())

    if request.method == 'PUT':
        data = request.get_json()
        autor.nome = data.get('nome', autor.nome)
        autor.nascimento = data.get('nascimento', autor.nascimento)
        db.session.commit()
        return jsonify(autor.to_dict())

    if request.method == 'DELETE':
        # Nota: O relacionamento 'cascade' em Autor deletará livros associados.
        db.session.delete(autor)
        db.session.commit()
        return jsonify({'mensagem': f'Autor {autor.nome} deletado com sucesso!'})
    
    # =======================================================
# 5. ROTAS PARA LIVROS
# =======================================================

# Rota GET (Listar) e POST (Criar)
@app.route('/api/livros', methods=['GET', 'POST'])
def handle_livros():
    if request.method == 'GET':
        livros = Livro.query.all()
        return jsonify([livro.to_dict() for livro in livros])

    if request.method == 'POST':
        data = request.get_json()
        if not all(k in data for k in ('titulo', 'isbn', 'autor_id')):
            return jsonify({'erro': 'Campos obrigatórios (titulo, isbn, autor_id) estão faltando.'}), 400

        if Autor.query.get(data['autor_id']) is None:
            return jsonify({'erro': 'Autor ID não encontrado.'}), 404
            
        if Livro.query.filter_by(isbn=data['isbn']).first():
            return jsonify({'erro': 'ISBN já cadastrado.'}), 409

        novo_livro = Livro(
            titulo=data['titulo'], ano_publicacao=data.get('ano_publicacao'),
            isbn=data['isbn'], autor_id=data['autor_id']
        )
        db.session.add(novo_livro)
        db.session.commit()
        return jsonify(novo_livro.to_dict()), 201

# Rota GET/PUT/DELETE por ID
@app.route('/api/livros/<int:livro_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_livro(livro_id):
    livro = Livro.query.get_or_404(livro_id) 

    if request.method == 'GET':
        return jsonify(livro.to_dict())

    if request.method == 'PUT':
        data = request.get_json()
        livro.titulo = data.get('titulo', livro.titulo)
        livro.ano_publicacao = data.get('ano_publicacao', livro.ano_publicacao)
        
        if 'autor_id' in data:
            if Autor.query.get(data['autor_id']) is None:
                return jsonify({'erro': 'Novo Autor ID não encontrado.'}), 404
            livro.autor_id = data['autor_id']
            
        db.session.commit()
        return jsonify(livro.to_dict())

    if request.method == 'DELETE':
        db.session.delete(livro)
        db.session.commit()
        return jsonify({'mensagem': f'Livro {livro.titulo} deletado com sucesso!'}), 200
    # =======================================================
# 6. EXECUÇÃO DA APLICAÇÃO
if __name__ == '__main__':
    # Roda o servidor de desenvolvimento
    app.run(debug=True)    