import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date

basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-should-be-more-complex'
# データベースの接続設定をRender用に変更
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', f"sqlite:///{os.path.join(basedir, 'app.db')}")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- ▼▼▼ データベースモデルの変更 ▼▼▼ ---
class StudyMaterial(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    total_units = db.Column(db.Integer, nullable=False)
    # 完了したユニット番号をカンマ区切りの文字列で保存 (例: "1,5,10")
    completed_list = db.Column(db.Text, default='')
    target_date = db.Column(db.Date, nullable=True)
    category = db.Column(db.String(50), nullable=False, default='未分類')

    def __repr__(self):
        return f'<StudyMaterial {self.name}>'

    # --- ▼▼▼ 完了数を計算するプロパティを追加 ▼▼▼ ---
    @property
    def completed_units(self):
        if not self.completed_list:
            return 0
        # カンマで区切って空白を除いたリストを作り、その長さを返す
        return len([item for item in self.completed_list.split(',') if item.strip()])

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

        # remaining_daysが0より大きいことを確認
        if remaining_days > 0:
            pace = remaining_units / remaining_days
            return f"残り{remaining_days}日 (1日あたり約 {pace:.1f} のペース)"
        else:
            return "ペース計算不可"


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

# --- ▼▼▼ 進捗更新ロジックの変更 ▼▼▼ ---
@app.route('/update/<int:material_id>', methods=['POST'])
def update(material_id):
    material = StudyMaterial.query.get_or_404(material_id)
    # フォームからテキストとして受け取る
    new_completed_list = request.form.get('completed_list')

    if new_completed_list is not None:
        # 入力された番号を検証・整形する
        try:
            # カンマやスペースで区切られた数値をリストに変換
            items = [str(int(i.strip())) for i in new_completed_list.replace(',', ' ').split() if i.strip().isdigit()]
            # 重複を除いてソート
            unique_items = sorted(list(set(items)), key=int)
            material.completed_list = ','.join(unique_items)
            db.session.commit()
            flash("進捗を更新しました！", "success")
        except ValueError:
            flash("数値として認識できない入力がありました。", "danger")

    return redirect(request.referrer or url_for('index'))


@app.route('/delete/<int:material_id>', methods=['POST'])
def delete(material_id):
    material = StudyMaterial.query.get_or_404(material_id)
    db.session.delete(material)
    db.session.commit()
    flash(f"「{material.name}」を削除しました。", "info")
    return redirect(request.referrer or url_for('index'))

# --- ▼▼▼ データベース初期化のためのコマンド（変更なし）▼▼▼ ---
@app.cli.command('init-db')
def init_db_command():
    """データベースを初期化します。"""
    db.create_all()
    print('データベースを初期化しました。')

# --- ▼▼▼ ローカル実行時のデータベース作成（変更なし）▼▼▼ ---
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
