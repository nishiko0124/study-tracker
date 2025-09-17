import os
from flask import Flask, render_template, request, redirect, url_for, flash # flashを追加
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date

basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
# flashメッセージのためにSECRET_KEYを設定
app.config['SECRET_KEY'] = 'your-secret-key-should-be-more-complex' # 実際にはもっと複雑な文字列にしてください
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


class StudyMaterial(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    total_units = db.Column(db.Integer, nullable=False)
    completed_units = db.Column(db.Integer, default=0)
    target_date = db.Column(db.Date, nullable=True)
    category = db.Column(db.String(50), nullable=False, default='未分類')

    def __repr__(self):
        return f'<StudyMaterial {self.name}>'

    @property
    def pace_info(self):
        if not self.target_date:
            return "目標日が設定されていません"

        today = date.today()
        remaining_days = (self.target_date - today).days
        remaining_units = self.total_units - self.completed_units

        if remaining_units <= 0:
            return "🎉 完了！"
        if remaining_days < 0:
            return "目標日を過ぎています！"
        if remaining_days == 0:
            return f"今日中に残り {remaining_units} を終わらせましょう！"

        pace = remaining_units / remaining_days
        return f"残り{remaining_days}日 (1日あたり約 {pace:.1f} のペース)"


@app.route('/', defaults={'selected_category': 'all'})
@app.route('/category/<selected_category>')
def index(selected_category):
    all_categories = db.session.query(StudyMaterial.category).distinct().all()
    categories = sorted([c[0] for c in all_categories])

    if selected_category == 'all':
        materials = StudyMaterial.query.order_by(db.nullslast(StudyMaterial.target_date.asc())).all()
    else:
        materials = StudyMaterial.query.filter_by(category=selected_category).order_by(db.nullslast(StudyMaterial.target_date.asc())).all()

    return render_template('index.html', materials=materials, categories=categories, current_category=selected_category)


@app.route('/add', methods=['POST'])
def add_material():
    material_name = request.form['name']
    total_units = int(request.form['total_units'])
    category = request.form.get('category', '未分類').strip()
    if not category:
        category = '未分類'

    target_date_str = request.form['target_date']
    target_date = None
    if target_date_str:
        target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()

    new_material = StudyMaterial(
        name=material_name,
        total_units=total_units,
        category=category,
        target_date=target_date
    )
    db.session.add(new_material)
    db.session.commit()
    flash(f"「{material_name}」を登録しました！", "success")
    return redirect(url_for('index'))


@app.route('/update/<int:material_id>', methods=['POST'])
def update(material_id):
    material = StudyMaterial.query.get_or_404(material_id)
    new_completed = request.form.get('completed_units')

    if new_completed and new_completed.isdigit():
        completed = int(new_completed)
        if 0 <= completed <= material.total_units:
            material.completed_units = completed
            db.session.commit()
            flash("進捗を更新しました！", "success")
        else:
            flash("無効な数値です。", "danger")

    return redirect(request.referrer or url_for('index'))


@app.route('/delete/<int:material_id>', methods=['POST'])
def delete(material_id):
    material = StudyMaterial.query.get_or_404(material_id)
    db.session.delete(material)
    db.session.commit()
    flash(f"「{material.name}」を削除しました。", "info")
    return redirect(request.referrer or url_for('index'))


@app.cli.command('init-db')
def init_db_command():
    db.create_all()
    print('データベースを初期化しました。')


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
