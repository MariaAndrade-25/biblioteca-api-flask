from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import json  # importei caso precise trabalhar com JSON manualmente depois

# inicializando a aplicação Flask
app = Flask(__name__)

# configuração do banco SQLite
# o arquivo database.db será criado automaticamente
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'

# desativei isso para evitar warnings do SQLAlchemy
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# conectando o SQLAlchemy com a aplicação Flask
db = SQLAlchemy(app)


# model da tabela de autores
class Autor(db.Model):

    # chave primária da tabela
    id = db.Column(db.Integer, primary_key=True)

    # nullable=False deixa o campo obrigatório
    nome = db.Column(db.String(100), nullable=False)

    nascimento = db.Column(db.String(10))

    # relacionamento: um autor pode ter vários livros
    # cascade faz os livros serem deletados junto com o autor
    livros = db.relationship(
        'Livro',
        backref='autor',
        lazy=True,
        cascade="all, delete-orphan"
    )

    # método para transformar objeto em dicionário/JSON
    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'nascimento': self.nascimento,

            # contando quantos livros o autor possui
            'livros_count': len(self.livros)
        }


# model da tabela de livros
class Livro(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    titulo = db.Column(db.String(200), nullable=False)

    ano_publicacao = db.Column(db.Integer)

    # unique=True impede ISBN repetido
    isbn = db.Column(db.String(20), unique=True, nullable=False)

    # foreign key ligando livro ao autor
    autor_id = db.Column(
        db.Integer,
        db.ForeignKey('autor.id'),
        nullable=False
    )

    def to_dict(self):
        return {
            'id': self.id,
            'titulo': self.titulo,
            'ano_publicacao': self.ano_publicacao,
            'isbn': self.isbn,
            'autor_id': self.autor_id,

            # usando o relacionamento para acessar o nome do autor
            'nome_autor': self.autor.nome
        }


# comando para criar as tabelas do banco
# roda no terminal com: flask init-db
@app.cli.command('init-db')
def init_db_command():

    # criando contexto da aplicação para acessar o banco
    with app.app_context():

        # cria todas as tabelas definidas nas models
        db.create_all()

        print('Banco de dados e tabelas criados com sucesso!')


# =======================================================
# ROTAS AUTORES
# =======================================================

# GET -> listar autores
# POST -> criar autor
@app.route('/api/autores', methods=['GET', 'POST'])
def handle_autores():

    # listando todos os autores
    if request.method == 'GET':

        autores = Autor.query.all()

        # convertendo objetos para JSON
        return jsonify([autor.to_dict() for autor in autores])

    # criando novo autor
    if request.method == 'POST':

        # pegando JSON enviado na requisição
        data = request.get_json()

        # validação simples
        if not data or 'nome' not in data:
            return jsonify({
                'erro': 'Nome do autor é obrigatório.'
            }), 400

        # criando objeto Autor
        novo_autor = Autor(
            nome=data['nome'],
            nascimento=data.get('nascimento')
        )

        # adiciona na sessão do banco
        db.session.add(novo_autor)

        # salva definitivamente
        db.session.commit()

        return jsonify(novo_autor.to_dict()), 201


# GET -> buscar por id
# PUT -> atualizar
# DELETE -> deletar
@app.route('/api/autores/<int:autor_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_autor(autor_id):

    # busca autor pelo id
    # se não existir retorna 404 automaticamente
    autor = Autor.query.get_or_404(autor_id)

    if request.method == 'GET':
        return jsonify(autor.to_dict())

    # atualizando dados do autor
    if request.method == 'PUT':

        data = request.get_json()

        # mantém valor antigo se nada for enviado
        autor.nome = data.get('nome', autor.nome)

        autor.nascimento = data.get(
            'nascimento',
            autor.nascimento
        )

        db.session.commit()

        return jsonify(autor.to_dict())

    # deletando autor
    if request.method == 'DELETE':

        # cascade também remove livros relacionados
        db.session.delete(autor)

        db.session.commit()

        return jsonify({
            'mensagem': f'Autor {autor.nome} deletado com sucesso!'
        })


# =======================================================
# ROTAS LIVROS
# =======================================================

# GET -> listar livros
# POST -> criar livro
@app.route('/api/livros', methods=['GET', 'POST'])
def handle_livros():

    if request.method == 'GET':

        livros = Livro.query.all()

        return jsonify([
            livro.to_dict() for livro in livros
        ])

    if request.method == 'POST':

        data = request.get_json()

        # validando campos obrigatórios
        if not all(
            k in data for k in ('titulo', 'isbn', 'autor_id')
        ):
            return jsonify({
                'erro': 'Campos obrigatórios estão faltando.'
            }), 400

        # verificando se o autor existe
        if Autor.query.get(data['autor_id']) is None:
            return jsonify({
                'erro': 'Autor ID não encontrado.'
            }), 404

        # evitando ISBN duplicado
        if Livro.query.filter_by(isbn=data['isbn']).first():
            return jsonify({
                'erro': 'ISBN já cadastrado.'
            }), 409

        novo_livro = Livro(
            titulo=data['titulo'],
            ano_publicacao=data.get('ano_publicacao'),
            isbn=data['isbn'],
            autor_id=data['autor_id']
        )

        db.session.add(novo_livro)

        db.session.commit()

        return jsonify(novo_livro.to_dict()), 201


# GET/PUT/DELETE livro por id
@app.route('/api/livros/<int:livro_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_livro(livro_id):

    livro = Livro.query.get_or_404(livro_id)

    if request.method == 'GET':
        return jsonify(livro.to_dict())

    # atualizando livro
    if request.method == 'PUT':

        data = request.get_json()

        livro.titulo = data.get(
            'titulo',
            livro.titulo
        )

        livro.ano_publicacao = data.get(
            'ano_publicacao',
            livro.ano_publicacao
        )

        # atualiza autor apenas se enviado
        if 'autor_id' in data:

            # validando novo autor
            if Autor.query.get(data['autor_id']) is None:
                return jsonify({
                    'erro': 'Novo Autor ID não encontrado.'
                }), 404

            livro.autor_id = data['autor_id']

        db.session.commit()

        return jsonify(livro.to_dict())

    # deletando livro
    if request.method == 'DELETE':

        db.session.delete(livro)

        db.session.commit()

        return jsonify({
            'mensagem': f'Livro {livro.titulo} deletado com sucesso!'
        }), 200


# =======================================================
# EXECUÇÃO DA APLICAÇÃO
# =======================================================

if __name__ == '__main__':

    # debug=True reinicia o servidor automaticamente
    # quando eu altero o código
    app.run(debug=True)
