import os
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date

# --- 基本設定 (変更なし) ---
basedir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'study.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- データベースのモデル定義 (カテゴリ列を追加) ---
class StudyMaterial(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    total_units = db.Column(db.Integer, nullable=False)
    completed_units = db.Column(db.Integer, default=0)
    target_date = db.Column(db.Date, nullable=True)
    category = db.Column(db.String(50), nullable=False, default='未分類') # カテゴリ列

    def __repr__(self):
        return f'<StudyMaterial {self.name}>'

# --- Webページのルーティング ---
# ▼▼▼ 変更: URLに<selected_category>を追加 ▼▼▼
@app.route('/', defaults={'selected_category': 'all'})
@app.route('/category/<selected_category>')
def index(selected_category):
    # すべてのカテゴリ名を取得してリストにする
    all_categories = db.session.query(StudyMaterial.category).distinct().all()
    # [(tuples),] の形式なので、[string,] の形式に変換
    categories = sorted([c[0] for c in all_categories])

    # 教材リストを取得
    if selected_category == 'all':
        # すべての教材を取得
        materials = StudyMaterial.query.order_by(StudyMaterial.id).all()
    else:
        # 選択されたカテゴリで絞り込んで取得
        materials = StudyMaterial.query.filter_by(category=selected_category).order_by(StudyMaterial.id).all()

    # 自動計算ロジック (変更なし)
    today = date.today()
    for material in materials:
        material.pace_info = "目標日が設定されていません"
        if material.target_date:
            remaining_days = (material.target_date - today).days
            remaining_units = material.total_units - material.completed_units
            if remaining_units <= 0:
                material.pace_info = "🎉 完了！"
            elif remaining_days < 0:
                material.pace_info = "目標日を過ぎています！"
            elif remaining_days == 0:
                material.pace_info = f"今日中に残り {remaining_units} を終わらせましょう！"
            else:
                pace = remaining_units / remaining_days
                material.pace_info = f"残り{remaining_days}日 (1日あたり約 {pace:.1f} のペース)"

    return render_template('index.html', materials=materials, categories=categories, current_category=selected_category)

# ▼▼▼ 追加: 新規教材を登録するための処理 ▼▼▼
@app.route('/add', methods=['POST'])
def add_material():
    material_name = request.form['name']
    total_units = int(request.form['total_units'])
    # ▼▼▼ カテゴリを取得 ▼▼▼
    category = request.form.get('category', '未分類').strip()
    if not category: # もし入力が空なら「未分類」にする
        category = '未分類'

    target_date_str = request.form['target_date']
    target_date = None
    if target_date_str:
        target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()

    new_material = StudyMaterial(
        name=material_name,
        total_units=total_units,
        category=category, # DBに保存
        target_date=target_date
    )
    db.session.add(new_material)
    db.session.commit()
    return redirect(url_for('index'))


# --- 更新・削除処理 (変更なし) ---
@app.route('/update/<int:material_id>', methods=['POST'])
def update(material_id):
    material = StudyMaterial.query.get_or_404(material_id)
    new_completed = request.form.get('completed_units')
    if new_completed and new_completed.isdigit():
        material.completed_units = int(new_completed)
        db.session.commit()
    return redirect(request.referrer or url_for('index')) # 元のページに戻る

@app.route('/delete/<int:material_id>', methods=['POST'])
def delete(material_id):
    material = StudyMaterial.query.get_or_404(material_id)
    db.session.delete(material)
    db.session.commit()
    return redirect(request.referrer or url_for('index')) # 元のページに戻る

# --- データベース初期化コマンド (変更なし) ---
@app.cli.command('init-db')
def init_db_command():
    db.create_all()
    print('データベースを初期化しました。')

# --- 実行 (変更なし) ---
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
