import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date

basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-should-be-more-complex'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# データベースの変更点: completed_units を文字列型に
class StudyMaterial(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    total_units = db.Column(db.Integer, nullable=False)
    # 変更: completed_units を文字列型(完了したユニット番号をカンマ区切りで保存)に変更
    completed_units = db.Column(db.String(500), default='')
    target_date = db.Column(db.Date, nullable=True)
    category = db.Column(db.String(50), nullable=False, default='未分類')

    def __repr__(self):
        return f'<StudyMaterial {self.name}>'

    # 進捗の計算方法を変更
    @property
    def completed_count(self):
        # カンマ区切りの文字列をリストに変換し、要素数を返す
        if not self.completed_units:
            return 0
        # 重複を考慮してset()を使用
        return len(set(self.completed_units.split(',')))

    @property
    def pace_info(self):
        if not self.target_date:
            return "目標日が設定されていません"

        today = date.today()
        remaining_days = (self.target_date - today).days
        remaining_units = self.total_units - self.completed_count

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
    new_unit = request.form.get('completed_unit') # フォーム入力欄の名前を変更

    if new_unit and new_unit.isdigit():
        unit_number = int(new_unit)
        if 1 <= unit_number <= material.total_units:
            # 既に登録済みのユニットリストを取得
            completed_list = material.completed_units.split(',') if material.completed_units else []
            # 新しいユニット番号を追加
            completed_list.append(str(unit_number))
            # 重複を削除してソート
            completed_list = sorted(list(set(completed_list)), key=int)
            # カンマ区切りの文字列に戻して保存
            material.completed_units = ','.join(completed_list)
            db.session.commit()
            flash("進捗を更新しました！", "success")
        else:
            flash(f"ユニット番号は1から{material.total_units}の範囲で入力してください。", "danger")
    else:
        flash("有効なユニット番号を入力してください。", "danger")

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
        # データベースを初期化（既存のテーブルは削除されるので注意）
        db.drop_all() # 既存のテーブルを一度削除
        db.create_all() # 新しいテーブルを作成
    app.run(debug=True)
