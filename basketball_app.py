import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import datetime
import os

# ========== 数据库初始化函数 ==========
def init_database():
    """初始化数据库表结构"""
    conn = sqlite3.connect('basketball.db')
    cursor = conn.cursor()
    
    # 创建球队表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS teams (
            team_id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_name TEXT NOT NULL UNIQUE,
            created_date DATE DEFAULT CURRENT_DATE
        )
    """)
    
    # 创建球员表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS players (
            player_id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_name TEXT NOT NULL,
            team_id INTEGER,
            jersey_number INTEGER DEFAULT 0,
            FOREIGN KEY (team_id) REFERENCES teams(team_id)
        )
    """)
    
    # 创建比赛表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS matches (
            match_id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_date DATE NOT NULL,
            game_type TEXT DEFAULT '5v5',
            home_team_id INTEGER,
            away_team_id INTEGER,
            home_win INTEGER DEFAULT 0,
            away_win INTEGER DEFAULT 0,
            FOREIGN KEY (home_team_id) REFERENCES teams(team_id),
            FOREIGN KEY (away_team_id) REFERENCES teams(team_id)
        )
    """)
    
    # 检查并添加 match_name 字段
    cursor.execute("PRAGMA table_info(matches)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'match_name' not in columns:
        try:
            cursor.execute("ALTER TABLE matches ADD COLUMN match_name TEXT")
            print("✅ 添加 match_name 字段成功")
        except Exception as e:
            print(f"添加 match_name 字段失败: {e}")
    
    # 创建球员统计表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS player_stats (
            stat_id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER,
            match_id INTEGER,
            points INTEGER DEFAULT 0,
            rebounds INTEGER DEFAULT 0,
            assists INTEGER DEFAULT 0,
            steals INTEGER DEFAULT 0,
            blocks INTEGER DEFAULT 0,
            turnovers INTEGER DEFAULT 0,
            fouls INTEGER DEFAULT 0,
            minutes_played REAL DEFAULT 0,
            fg2_made INTEGER DEFAULT 0,
            fg2_attempts INTEGER DEFAULT 0,
            fg3_made INTEGER DEFAULT 0,
            fg3_attempts INTEGER DEFAULT 0,
            ft_made INTEGER DEFAULT 0,
            ft_attempts INTEGER DEFAULT 0,
            is_home INTEGER DEFAULT 1,
            FOREIGN KEY (player_id) REFERENCES players(player_id),
            FOREIGN KEY (match_id) REFERENCES matches(match_id)
        )
    """)
    
    conn.commit()
    conn.close()
    print("✅ 数据库初始化完成")

# ========== 更新已有数据的 match_name ==========
def update_existing_matches():
    """为已有的比赛设置默认的 match_name"""
    conn = sqlite3.connect('basketball.db')
    cursor = conn.cursor()
    
    # 检查是否有 match_name 为空的记录
    cursor.execute("SELECT match_id, match_date FROM matches WHERE match_name IS NULL")
    null_matches = cursor.fetchall()
    
    for match_id, match_date in null_matches:
        # 获取当天已有多少场比赛
        cursor.execute("""
            SELECT COUNT(*) FROM matches 
            WHERE match_date = ? AND match_name IS NOT NULL
        """, (match_date,))
        count = cursor.fetchone()[0]
        
        # 设置默认名称
        default_name = f"第{count + 1}场"
        cursor.execute("UPDATE matches SET match_name = ? WHERE match_id = ?", 
                      (default_name, match_id))
        print(f"✅ 更新比赛 {match_date} 为 {default_name}")
    
    conn.commit()
    conn.close()

# ========== 页面配置 ==========
st.set_page_config(page_title="小东瓜数据统计系统", page_icon="🏀", layout="wide")

# ========== 初始化数据库 ==========
init_database()

# ========== 更新已有数据 ==========
update_existing_matches()

# ========== 连接数据库 ==========
conn = sqlite3.connect('basketball.db', check_same_thread=False)

# ========== 主页面标题 ==========
st.title("小东瓜数据统计系统")

# ========== 侧边栏菜单 ==========
menu = st.sidebar.selectbox("菜单", [ "📊 球员数据榜", "📋 比赛记录", "📝 数据录入", "⚙️ 管理后台"])

# ==================== 数据录入 ====================
if menu == "📝 数据录入":
    st.header("📝 录入本场数据")
    
    # 获取所有比赛（包含match_name）
    matches = pd.read_sql("""
        SELECT m.match_id, m.match_date, m.match_name, m.game_type,
               CASE 
                   WHEN m.home_team_id IS NOT NULL THEN t1.team_name 
                   ELSE '队伍1' 
               END as home_team,
               CASE 
                   WHEN m.away_team_id IS NOT NULL THEN t2.team_name 
                   ELSE '队伍2' 
               END as away_team
        FROM matches m
        LEFT JOIN teams t1 ON m.home_team_id = t1.team_id
        LEFT JOIN teams t2 ON m.away_team_id = t2.team_id
        ORDER BY m.match_date DESC, m.match_name
    """, conn)
    
    if matches.empty:
        st.warning("请先在管理后台添加比赛")
    else:
        # 比赛选择（显示日期+场次）
        match_options = []
        game_type_display_map = {"5v5": "5v5全场", "4v4": "4v4半场抢分21", "3v3": "3v3半场抢分21"}
        for _, row in matches.iterrows():
            game_type_display = game_type_display_map.get(row['game_type'], row['game_type'])
            match_options.append(f"{row['match_date']} {row['match_name']} | {game_type_display} | {row['home_team']} vs {row['away_team']}")
        
        selected_match = st.selectbox("选择比赛", match_options, key="match_select")
        selected_idx = match_options.index(selected_match)
        match_data = matches.iloc[selected_idx]
        match_id = int(match_data['match_id'])
        
        # 显示比赛胜负设置
        st.subheader("🏆 比赛结果")
        col_win1, col_win2 = st.columns(2)
        with col_win1:
            home_win = st.checkbox(f"{match_data['home_team']} 获胜", key="home_win")
        with col_win2:
            away_win = st.checkbox(f"{match_data['away_team']} 获胜", key="away_win")
        
        # 更新比赛胜负
        if st.button("更新比赛结果", key="update_match_result"):
            conn.execute("UPDATE matches SET home_win = ?, away_win = ? WHERE match_id = ?",
                        (1 if home_win else 0, 1 if away_win else 0, match_id))
            conn.commit()
            st.success("✅ 比赛结果已更新")
            st.rerun()
        
        st.divider()
        
        # 获取所有球员
        players = pd.read_sql("SELECT player_id, player_name FROM players ORDER BY player_name", conn)
        
        if players.empty:
            st.warning("请先在管理后台添加球员")
        else:
            # 球员选择
            selected_player = st.selectbox("选择球员", players['player_id'], 
                                         format_func=lambda x: players[players['player_id']==x]['player_name'].values[0],
                                         key="player_select")
            
            # 主客队选择
            is_home = st.radio(
                "球员所在队伍",
                [f"🏠 {match_data['home_team']}", f"✈️ {match_data['away_team']}"],
                horizontal=True,
                key="home_away"
            )
            is_home_value = 1 if "🏠" in is_home else 0
            
            # 检查是否已有该球员本场比赛的数据
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM player_stats 
                WHERE player_id = ? AND match_id = ?
            """, (int(selected_player), int(match_id)))
            
            existing_data = cursor.fetchone()
            
            if existing_data:
                st.warning("⚠️ 该球员本场比赛已有数据，将进行更新")
                # 获取列名
                cursor.execute("PRAGMA table_info(player_stats)")
                columns = [col[1] for col in cursor.fetchall()]
                # 创建字典
                default_values = dict(zip(columns, existing_data))
                st.info(f"当前数据：得分 {default_values['points']}分，篮板 {default_values['rebounds']}个")
            else:
                default_values = None
                st.success("✅ 可以录入新数据")
            
            # 投篮数据
            st.subheader("🏹 投篮数据")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.write("**两分球**")
                fg2_m = st.number_input("命中", 0, 50, value=int(default_values['fg2_made']) if default_values else 0, key="fg2m")
                fg2_a = st.number_input("出手", 0, 50, value=int(default_values['fg2_attempts']) if default_values else 0, key="fg2a")
                if fg2_a > 0:
                    st.caption(f"命中率: {fg2_m/fg2_a*100:.1f}%")
            
            with col2:
                st.write("**三分球**")
                fg3_m = st.number_input("命中", 0, 50, value=int(default_values['fg3_made']) if default_values else 0, key="fg3m")
                fg3_a = st.number_input("出手", 0, 50, value=int(default_values['fg3_attempts']) if default_values else 0, key="fg3a")
                if fg3_a > 0:
                    st.caption(f"命中率: {fg3_m/fg3_a*100:.1f}%")
            
            with col3:
                st.write("**罚球**")
                ft_m = st.number_input("命中", 0, 50, value=int(default_values['ft_made']) if default_values else 0, key="ftm")
                ft_a = st.number_input("出手", 0, 50, value=int(default_values['ft_attempts']) if default_values else 0, key="fta")
                if ft_a > 0:
                    st.caption(f"命中率: {ft_m/ft_a*100:.1f}%")
            
            # 得分和其他数据
            st.subheader("📊 其他数据")
            total_points = st.number_input("总得分", 0, 100, value=int(default_values['points']) if default_values else 0, key="points")
            
            col4, col5, col6 = st.columns(3)
            with col4:
                rebounds = st.number_input("篮板", 0, 50, value=int(default_values['rebounds']) if default_values else 0, key="reb")
                assists = st.number_input("助攻", 0, 30, value=int(default_values['assists']) if default_values else 0, key="ast")
            with col5:
                steals = st.number_input("抢断", 0, 20, value=int(default_values['steals']) if default_values else 0, key="stl")
                blocks = st.number_input("盖帽", 0, 20, value=int(default_values['blocks']) if default_values else 0, key="blk")
            with col6:
                turnovers = st.number_input("失误", 0, 20, value=int(default_values['turnovers']) if default_values else 0, key="to")
                fouls = st.number_input("犯规", 0, 6, value=int(default_values['fouls']) if default_values else 0, key="fls")
            
            # 保存按钮
            if st.button("💾 保存数据", type="primary"):
                try:
                    # 确保所有ID都是整数
                    player_id = int(selected_player)
                    match_id_int = int(match_id)
                    
                    if existing_data:
                        # 更新现有数据
                        cursor.execute("""
                            UPDATE player_stats 
                            SET points = ?, rebounds = ?, assists = ?, steals = ?, blocks = ?, 
                                turnovers = ?, fouls = ?, fg2_made = ?, fg2_attempts = ?, 
                                fg3_made = ?, fg3_attempts = ?, ft_made = ?, ft_attempts = ?,
                                is_home = ?
                            WHERE player_id = ? AND match_id = ?
                        """, (total_points, rebounds, assists, steals, blocks, turnovers, fouls,
                              fg2_m, fg2_a, fg3_m, fg3_a, ft_m, ft_a, is_home_value,
                              player_id, match_id_int))
                        conn.commit()
                        st.success("✅ 数据更新成功！")
                        st.balloons()
                    else:
                        # 插入新数据
                        cursor.execute("""
                            INSERT INTO player_stats 
                            (player_id, match_id, points, rebounds, assists, steals, blocks, turnovers, fouls,
                             fg2_made, fg2_attempts, fg3_made, fg3_attempts, ft_made, ft_attempts, is_home)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (player_id, match_id_int, total_points, rebounds, assists, steals, blocks, turnovers, fouls,
                              fg2_m, fg2_a, fg3_m, fg3_a, ft_m, ft_a, is_home_value))
                        conn.commit()
                        st.success("✅ 数据保存成功！")
                        st.balloons()
                    
                except Exception as e:
                    st.error(f"❌ 保存失败：{e}")

# ==================== 球员数据榜 ====================
elif menu == "📊 球员数据榜":
    st.header("📊 球员数据榜")
    
    # 比赛类型筛选
    col1, col2 = st.columns([1, 3])
    with col1:
        game_type_filter = st.selectbox(
            "🏀 比赛类型",
            ["全部", "5v5全场", "4v4半场抢分21", "3v3半场抢分21"],
            index=0
        )
    
    # 转换筛选条件
    game_type_map = {
        "5v5全场": "5v5",
        "4v4半场抢分21": "4v4",
        "3v3半场抢分21": "3v3"
    }
    
    # 构建带筛选的查询
    where_clause = ""
    if game_type_filter != "全部":
        game_type_code = game_type_map[game_type_filter]
        where_clause = f"AND m.game_type = '{game_type_code}'"
    
    # 查询数据
    query = f"""
        SELECT 
            p.player_name,
            COUNT(DISTINCT ps.match_id) as games,
            -- 场均数据
            ROUND(AVG(ps.points), 1) as avg_points,
            ROUND(AVG(ps.rebounds), 1) as avg_rebounds,
            ROUND(AVG(ps.assists), 1) as avg_assists,
            ROUND(AVG(ps.steals), 1) as avg_steals,
            ROUND(AVG(ps.blocks), 1) as avg_blocks,
            ROUND(AVG(ps.turnovers), 1) as avg_turnovers,
            ROUND(AVG(ps.fouls), 1) as avg_fouls,
            ROUND(AVG(ps.fg2_made), 1) as avg_fg2_made,
            ROUND(AVG(ps.fg2_attempts), 1) as avg_fg2_att,
            ROUND(AVG(ps.fg3_made), 1) as avg_fg3_made,
            ROUND(AVG(ps.fg3_attempts), 1) as avg_fg3_att,
            ROUND(AVG(ps.ft_made), 1) as avg_ft_made,
            ROUND(AVG(ps.ft_attempts), 1) as avg_ft_att,
            -- 总数数据
            SUM(ps.points) as total_points,
            SUM(ps.rebounds) as total_rebounds,
            SUM(ps.assists) as total_assists,
            SUM(ps.steals) as total_steals,
            SUM(ps.blocks) as total_blocks,
            SUM(ps.turnovers) as total_turnovers,
            SUM(ps.fouls) as total_fouls,
            SUM(ps.fg2_made) as total_fg2_made,
            SUM(ps.fg2_attempts) as total_fg2_att,
            SUM(ps.fg3_made) as total_fg3_made,
            SUM(ps.fg3_attempts) as total_fg3_att,
            SUM(ps.ft_made) as total_ft_made,
            SUM(ps.ft_attempts) as total_ft_att
        FROM player_stats ps
        JOIN players p ON ps.player_id = p.player_id
        JOIN matches m ON ps.match_id = m.match_id
        WHERE 1=1 {where_clause}
        GROUP BY p.player_id
        ORDER BY avg_points DESC
    """
    
    try:
        df = pd.read_sql(query, conn)
        
        if not df.empty:
            if game_type_filter != "全部":
                st.info(f"🏀 当前筛选：{game_type_filter}")
            
            # 计算命中率
            df['fg2_pct'] = (df['total_fg2_made'] / df['total_fg2_att'] * 100).round(1)
            df['fg3_pct'] = (df['total_fg3_made'] / df['total_fg3_att'] * 100).round(1)
            df['ft_pct'] = (df['total_ft_made'] / df['total_ft_att'] * 100).round(1)
            
            # ===== 场均数据表格 =====
            st.subheader("📈 场均数据")
            avg_df = df[['player_name', 'games', 'avg_points', 'avg_rebounds', 'avg_assists', 
                         'avg_steals', 'avg_blocks', 'avg_turnovers', 'avg_fouls',
                         'avg_fg2_made', 'avg_fg2_att', 'avg_fg3_made', 'avg_fg3_att', 
                         'avg_ft_made', 'avg_ft_att', 'fg2_pct', 'fg3_pct', 'ft_pct']].copy()
            
            avg_df.columns = ['球员', '场次', '得分', '篮板', '助攻', '抢断', '盖帽', '失误', '犯规',
                              '两分中', '两分投', '三分中', '三分投', '罚球中', '罚球投',
                              '两分%', '三分%', '罚球%']
            st.dataframe(avg_df, use_container_width=True)
            
            st.divider()
            
            # ===== 总数数据表格 =====
            st.subheader("📊 总数数据")
            total_df = df[['player_name', 'games', 'total_points', 'total_rebounds', 'total_assists',
                           'total_steals', 'total_blocks', 'total_turnovers', 'total_fouls',
                           'total_fg2_made', 'total_fg2_att', 'total_fg3_made', 'total_fg3_att',
                           'total_ft_made', 'total_ft_att', 'fg2_pct', 'fg3_pct', 'ft_pct']].copy()
            
            total_df.columns = ['球员', '场次', '总得分', '总篮板', '总助攻', '总抢断', '总盖帽', 
                                '总失误', '总犯规', '两分总中', '两分总投', '三分总中', '三分总投',
                                '罚球总中', '罚球总投', '两分%', '三分%', '罚球%']
            st.dataframe(total_df, use_container_width=True)
            
            # 统计信息
            st.caption(f"📊 总计 {len(df)} 名球员，共 {df['games'].sum()} 场比赛")
            
        else:
            st.warning(f"暂无 {game_type_filter} 类型的数据")
            
            # 调试信息
            with st.expander("🔧 调试信息"):
                player_count = pd.read_sql("SELECT COUNT(*) as cnt FROM players", conn).iloc[0]['cnt']
                match_count = pd.read_sql("SELECT COUNT(*) as cnt FROM matches", conn).iloc[0]['cnt']
                stats_count = pd.read_sql("SELECT COUNT(*) as cnt FROM player_stats", conn).iloc[0]['cnt']
                
                st.write(f"👤 球员数量: {player_count}")
                st.write(f"📅 比赛数量: {match_count}")
                st.write(f"📊 统计数据条数: {stats_count}")
                
                if stats_count > 0:
                    st.write("原始统计数据：")
                    raw_data = pd.read_sql("SELECT * FROM player_stats LIMIT 5", conn)
                    st.dataframe(raw_data)
    except Exception as e:
        st.error(f"查询出错: {e}")

# ==================== 比赛记录 ====================
elif menu == "📋 比赛记录":
    st.header("📋 比赛记录")
    
    # 查询所有比赛
    matches = pd.read_sql("""
        SELECT m.match_id, m.match_date, m.match_name, m.game_type, m.home_win, m.away_win,
               CASE 
                   WHEN m.home_team_id IS NOT NULL THEN t1.team_name 
                   ELSE '队伍1' 
               END as home_team,
               CASE 
                   WHEN m.away_team_id IS NOT NULL THEN t2.team_name 
                   ELSE '队伍2' 
               END as away_team
        FROM matches m
        LEFT JOIN teams t1 ON m.home_team_id = t1.team_id
        LEFT JOIN teams t2 ON m.away_team_id = t2.team_id
        ORDER BY m.match_date DESC, m.match_name
    """, conn)
    
    game_type_display_map = {"5v5": "5v5全场", "4v4": "4v4半场抢分21", "3v3": "3v3半场抢分21"}
    
    for _, m in matches.iterrows():
        game_type_display = game_type_display_map.get(m['game_type'], m['game_type'])
        
        # 查询本场比赛的球员数据（用于预览）
        preview_stats = pd.read_sql(f"""
            SELECT 
                p.player_name,
                ps.is_home,
                ps.points
            FROM player_stats ps
            JOIN players p ON ps.player_id = p.player_id
            WHERE ps.match_id = {m['match_id']}
            ORDER BY ps.is_home, ps.points DESC
        """, conn)
        
        # 计算两队总得分和球员名单
        home_players = []
        away_players = []
        home_total = 0
        away_total = 0
        
        if not preview_stats.empty:
            home_stats = preview_stats[preview_stats['is_home'] == 1]
            away_stats = preview_stats[preview_stats['is_home'] == 0]
            
            home_players = home_stats['player_name'].tolist()
            away_players = away_stats['player_name'].tolist()
            home_total = home_stats['points'].sum()
            away_total = away_stats['points'].sum()
        
        # 确定获胜方
        winner = ""
        if m['home_win'] and m['away_win']:
            winner = "🤝 平局"
        elif m['home_win']:
            winner = f"🏆 {m['home_team']} 获胜"
        elif m['away_win']:
            winner = f"🏆 {m['away_team']} 获胜"
        
        # 创建预览文本
        preview_text = f"📅 {m['match_date']} {m['match_name']} [{game_type_display}]"
        preview_text += f"\n{m['home_team']} {home_total} : {away_total} {m['away_team']}"
        if winner:
            preview_text += f"  {winner}"
        
        # 添加球员预览
        if home_players or away_players:
            preview_text += "\n\n"
            if home_players:
                preview_text += f"🏠 {m['home_team']}: {', '.join(home_players[:3])}"
                if len(home_players) > 3:
                    preview_text += f" 等{len(home_players)}人"
            preview_text += "\n"
            if away_players:
                preview_text += f"✈️ {m['away_team']}: {', '.join(away_players[:3])}"
                if len(away_players) > 3:
                    preview_text += f" 等{len(away_players)}人"
        
        with st.expander(preview_text):
            # 查询本场比赛的所有球员数据（详细）
            all_stats_df = pd.read_sql(f"""
                SELECT 
                    ps.stat_id,
                    p.player_name,
                    ps.is_home,
                    ps.points,
                    ps.rebounds,
                    ps.assists,
                    ps.steals,
                    ps.blocks,
                    ps.turnovers,
                    ps.fouls,
                    ps.fg2_made,
                    ps.fg2_attempts,
                    ps.fg3_made,
                    ps.fg3_attempts,
                    ps.ft_made,
                    ps.ft_attempts
                FROM player_stats ps
                JOIN players p ON ps.player_id = p.player_id
                WHERE ps.match_id = {m['match_id']}
                ORDER BY ps.is_home DESC, ps.points DESC
            """, conn)
            
            if not all_stats_df.empty:
                # 分离主客队数据
                home_stats = all_stats_df[all_stats_df['is_home'] == 1].copy()
                away_stats = all_stats_df[all_stats_df['is_home'] == 0].copy()
                
                # 计算两队总得分（重新计算确保准确）
                home_total = home_stats['points'].sum() if not home_stats.empty else 0
                away_total = away_stats['points'].sum() if not away_stats.empty else 0
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric(f"{m['home_team']} 总得分", home_total)
                with col2:
                    st.metric(f"{m['away_team']} 总得分", away_total)
                with col3:
                    st.metric("分差", abs(home_total - away_total))
                
                st.markdown("---")
                
                # ===== 主队数据表格 =====
                if not home_stats.empty:
                    st.subheader(f"🏠 {m['home_team']}")
                    
                    # 使用HTML/CSS样式让表格更紧凑
                    st.markdown("""
                    <style>
                    .compact-table {
                        font-size: 16px;
                        line-height: 1.2;
                        margin-bottom: 5px;
                    }
                    .compact-table th {
                        background-color: #f0f2f6;
                        padding: 4px 8px;
                        text-align: center;
                        font-weight: 600;
                    }
                    .compact-table td {
                        padding: 2px 8px;
                        text-align: center;
                    }
                    .delete-btn {
                        color: #ff4b4b;
                        cursor: pointer;
                        font-size: 18px;
                    }
                    </style>
                    """, unsafe_allow_html=True)
                    
                    # 创建表头
                    cols = st.columns([2, 1, 1, 1, 1, 1, 1, 1, 2.5, 0.8])
                    headers = ['球员', '得分', '篮板', '助攻', '抢断', '盖帽', '失误', '犯规', '投篮', '操作']
                    for col, header in zip(cols, headers):
                        col.markdown(f"**{header}**")
                    
                    st.markdown("---")
                    
                    # 显示主队数据
                    for _, row in home_stats.iterrows():
                        cols = st.columns([2, 1, 1, 1, 1, 1, 1, 1, 2.5, 0.8])
                        
                        # 球员名
                        cols[0].markdown(f"**{row['player_name']}**")
                        
                        # 基础数据
                        cols[1].markdown(f"**{row['points']}**")
                        cols[2].markdown(f"**{row['rebounds']}**")
                        cols[3].markdown(f"**{row['assists']}**")
                        cols[4].markdown(f"**{row['steals']}**")
                        cols[5].markdown(f"**{row['blocks']}**")
                        cols[6].markdown(f"**{row['turnovers']}**")
                        cols[7].markdown(f"**{row['fouls']}**")
                        
                        # 投篮数据
                        fg2 = f"{row['fg2_made']}/{row['fg2_attempts']}" if row['fg2_attempts'] > 0 else "0/0"
                        fg3 = f"{row['fg3_made']}/{row['fg3_attempts']}" if row['fg3_attempts'] > 0 else "0/0"
                        ft = f"{row['ft_made']}/{row['ft_attempts']}" if row['ft_attempts'] > 0 else "0/0"
                        cols[8].markdown(f"**{fg2}** | **{fg3}** | **{ft}**")
                        
                        # 删除按钮
                        with cols[9]:
                            if st.button("🗑️", key=f"del_home_{row['stat_id']}", help="删除这条数据"):
                                try:
                                    conn.execute("DELETE FROM player_stats WHERE stat_id = ?", (row['stat_id'],))
                                    conn.commit()
                                    st.success(f"✅ 已删除 {row['player_name']} 的数据")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ 删除失败：{e}")
                        
                        st.markdown("---")
                else:
                    st.info(f"{m['home_team']} 暂无球员数据")
                
                st.markdown("---")
                
                # ===== 客队数据表格 =====
                if not away_stats.empty:
                    st.subheader(f"✈️ {m['away_team']}")
                    
                    # 创建表头
                    cols = st.columns([2, 1, 1, 1, 1, 1, 1, 1, 2.5, 0.8])
                    headers = ['球员', '得分', '篮板', '助攻', '抢断', '盖帽', '失误', '犯规', '投篮', '操作']
                    for col, header in zip(cols, headers):
                        col.markdown(f"**{header}**")
                    
                    st.markdown("---")
                    
                    # 显示客队数据
                    for _, row in away_stats.iterrows():
                        cols = st.columns([2, 1, 1, 1, 1, 1, 1, 1, 2.5, 0.8])
                        
                        # 球员名
                        cols[0].markdown(f"**{row['player_name']}**")
                        
                        # 基础数据
                        cols[1].markdown(f"**{row['points']}**")
                        cols[2].markdown(f"**{row['rebounds']}**")
                        cols[3].markdown(f"**{row['assists']}**")
                        cols[4].markdown(f"**{row['steals']}**")
                        cols[5].markdown(f"**{row['blocks']}**")
                        cols[6].markdown(f"**{row['turnovers']}**")
                        cols[7].markdown(f"**{row['fouls']}**")
                        
                        # 投篮数据
                        fg2 = f"{row['fg2_made']}/{row['fg2_attempts']}" if row['fg2_attempts'] > 0 else "0/0"
                        fg3 = f"{row['fg3_made']}/{row['fg3_attempts']}" if row['fg3_attempts'] > 0 else "0/0"
                        ft = f"{row['ft_made']}/{row['ft_attempts']}" if row['ft_attempts'] > 0 else "0/0"
                        cols[8].markdown(f"**{fg2}** | **{fg3}** | **{ft}**")
                        
                        # 删除按钮
                        with cols[9]:
                            if st.button("🗑️", key=f"del_away_{row['stat_id']}", help="删除这条数据"):
                                try:
                                    conn.execute("DELETE FROM player_stats WHERE stat_id = ?", (row['stat_id'],))
                                    conn.commit()
                                    st.success(f"✅ 已删除 {row['player_name']} 的数据")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ 删除失败：{e}")
                        
                        st.markdown("---")
                else:
                    st.info(f"{m['away_team']} 暂无球员数据")
                
                st.caption(f"本场共 {len(all_stats_df)} 名球员")
            else:
                st.info("暂无球员数据")
# ==================== 管理后台 ====================
elif menu == "⚙️ 管理后台":
    st.header("⚙️ 管理后台")
    
    # 创建三个标签页
    tab1, tab2, tab3 = st.tabs(["🏀 球队管理", "👤 球员管理", "📅 比赛管理"])
    
    # ========== 球队管理 ==========
    with tab1:
        st.subheader("添加球队")
        with st.form("add_team_form"):
            team_name = st.text_input("球队名称")
            if st.form_submit_button("添加球队"):
                if team_name:
                    try:
                        conn.execute("INSERT INTO teams (team_name) VALUES (?)", (team_name,))
                        conn.commit()
                        st.success(f"✅ 球队 {team_name} 添加成功")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ 添加失败：{e}")
        
        st.divider()
        st.subheader("现有球队")
        
        # 查询所有球队
        teams_df = pd.read_sql("""
            SELECT 
                t.team_id,
                t.team_name,
                t.created_date,
                COUNT(p.player_id) as player_count
            FROM teams t
            LEFT JOIN players p ON t.team_id = p.team_id
            GROUP BY t.team_id
            ORDER BY t.team_name
        """, conn)
        
        if not teams_df.empty:
            for _, row in teams_df.iterrows():
                col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                
                with col1:
                    st.write(f"**{row['team_name']}**")
                
                with col2:
                    st.write(f"{row['created_date']}")
                
                with col3:
                    st.write(f"{row['player_count']} 名球员")
                
                with col4:
                    # 删除按钮
                    if st.button("🗑️", key=f"del_team_{row['team_id']}", help="删除球队"):
                        if row['player_count'] > 0:
                            st.warning(f"该球队有 {row['player_count']} 名球员，无法删除")
                        else:
                            try:
                                conn.execute("DELETE FROM teams WHERE team_id = ?", (row['team_id'],))
                                conn.commit()
                                st.success(f"球队 {row['team_name']} 已删除")
                                st.rerun()
                            except Exception as e:
                                st.error(f"删除失败：{e}")
                
                st.divider()
            
            st.caption(f"总计 {len(teams_df)} 支球队")
        else:
            st.info("暂无球队")
    
    # ========== 球员管理 ==========
    with tab2:
        st.subheader("添加球员")
        with st.form("add_player_form"):
            player_name = st.text_input("球员姓名")
            jersey = st.number_input("球衣号码", 0, 99, 0)
            if st.form_submit_button("添加球员"):
                if player_name:
                    try:
                        conn.execute(
                            "INSERT INTO players (player_name, jersey_number) VALUES (?, ?)",
                            (player_name, jersey)
                        )
                        conn.commit()
                        st.success(f"球员 {player_name} 添加成功")
                        st.rerun()
                    except Exception as e:
                        st.error(f"添加失败：{e}")
        
        st.divider()
        st.subheader("现有球员")
        
        # 查询所有球员
        players_df = pd.read_sql("""
            SELECT 
                p.player_id,
                p.player_name,
                p.jersey_number,
                COUNT(ps.stat_id) as stats_count
            FROM players p
            LEFT JOIN player_stats ps ON p.player_id = ps.player_id
            GROUP BY p.player_id
            ORDER BY p.player_name
        """, conn)
        
        if not players_df.empty:
            for _, row in players_df.iterrows():
                col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                
                with col1:
                    st.write(f"**{row['player_name']}**")
                
                with col2:
                    st.write(f"#{row['jersey_number']}")
                
                with col3:
                    st.write(f"{row['stats_count']} 条记录")
                
                with col4:
                    # 删除按钮
                    if st.button("🗑️", key=f"del_player_{row['player_id']}", help="删除球员"):
                        if row['stats_count'] > 0:
                            st.warning(f"该球员有 {row['stats_count']} 条比赛记录，无法删除")
                        else:
                            try:
                                conn.execute("DELETE FROM players WHERE player_id = ?", (row['player_id'],))
                                conn.commit()
                                st.success(f"球员 {row['player_name']} 已删除")
                                st.rerun()
                            except Exception as e:
                                st.error(f"删除失败：{e}")
                
                st.divider()
            
            st.caption(f"总计 {len(players_df)} 名球员")
        else:
            st.info("暂无球员")
    
    # ========== 比赛管理 ==========
    with tab3:
        st.subheader("添加比赛")
        with st.form("add_match_form"):
            col1, col2 = st.columns(2)
            with col1:
                match_date = st.date_input("比赛日期")
            with col2:
                # 比赛名称选择
                match_name = st.selectbox(
                    "比赛场次",
                    ["第一场", "第二场", "第三场", "第四场", "第五场", "上午场", "下午场", "晚上场"],
                    index=0
                )
            
            game_type = st.selectbox(
                "比赛类型",
                ["5v5", "4v4", "3v3"],
                format_func=lambda x: {"5v5": "5v5全场", "4v4": "4v4半场抢分21", "3v3": "3v3半场抢分21"}[x]
            )
            
            # 获取球队列表
            teams_df = pd.read_sql("SELECT team_id, team_name FROM teams ORDER BY team_name", conn)
            team_options = [(None, "无球队（友谊赛）")] + [(row['team_id'], row['team_name']) for _, row in teams_df.iterrows()]
            
            col1, col2 = st.columns(2)
            with col1:
                home_team = st.selectbox(
                    "主队（可选）", 
                    [opt[0] for opt in team_options],
                    format_func=lambda x: next(opt[1] for opt in team_options if opt[0] == x),
                    key="home_team"
                )
            with col2:
                away_team = st.selectbox(
                    "客队（可选）", 
                    [opt[0] for opt in team_options],
                    format_func=lambda x: next(opt[1] for opt in team_options if opt[0] == x),
                    key="away_team",
                    index=1 if len(team_options) > 1 else 0
                )
            
            if st.form_submit_button("创建比赛"):
                if home_team is not None and away_team is not None and home_team == away_team:
                    st.error("主队和客队不能相同")
                else:
                    try:
                        conn.execute("""
                            INSERT INTO matches (match_date, match_name, game_type, home_team_id, away_team_id)
                            VALUES (?, ?, ?, ?, ?)
                        """, (match_date, match_name, game_type, home_team, away_team))
                        conn.commit()
                        st.success(f"✅ 比赛创建成功：{match_date} {match_name}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ 创建失败：{e}")
        
        st.divider()
        st.subheader("现有比赛")
        
        # 查询所有比赛
        matches_df = pd.read_sql("""
            SELECT 
                m.match_id,
                m.match_date,
                m.match_name,
                m.game_type,
                CASE 
                    WHEN m.home_team_id IS NOT NULL THEN t1.team_name 
                    ELSE '队伍1' 
                END as home_team,
                CASE 
                    WHEN m.away_team_id IS NOT NULL THEN t2.team_name 
                    ELSE '队伍2' 
                END as away_team,
                m.home_win,
                m.away_win,
                COUNT(ps.stat_id) as stats_count
            FROM matches m
            LEFT JOIN teams t1 ON m.home_team_id = t1.team_id
            LEFT JOIN teams t2 ON m.away_team_id = t2.team_id
            LEFT JOIN player_stats ps ON m.match_id = ps.match_id
            GROUP BY m.match_id
            ORDER BY m.match_date DESC, m.match_name
        """, conn)
        
        if not matches_df.empty:
            game_type_display_map = {"5v5": "5v5全场", "4v4": "4v4半场抢分21", "3v3": "3v3半场抢分21"}
            
            for _, row in matches_df.iterrows():
                game_type_display = game_type_display_map.get(row['game_type'], row['game_type'])
                
                # 确定获胜方
                winner = ""
                if row['home_win'] and row['away_win']:
                    winner = "平局"
                elif row['home_win']:
                    winner = f"{row['home_team']} 获胜"
                elif row['away_win']:
                    winner = f"{row['away_team']} 获胜"
                
                col1, col2, col3, col4, col5 = st.columns([2, 1.5, 2, 2, 1])
                
                with col1:
                    st.write(f"**{row['match_date']}**")
                
                with col2:
                    st.write(f"**{row['match_name']}**")
                
                with col3:
                    st.write(f"{game_type_display}")
                
                with col4:
                    st.write(f"{row['home_team']} vs {row['away_team']}")
                    if winner:
                        st.caption(winner)
                
                with col5:
                    # 删除按钮
                    if st.button("🗑️", key=f"del_match_{row['match_id']}", help="删除比赛"):
                        if row['stats_count'] > 0:
                            st.warning(f"该比赛有 {row['stats_count']} 条球员数据，无法删除")
                        else:
                            try:
                                conn.execute("DELETE FROM matches WHERE match_id = ?", (row['match_id'],))
                                conn.commit()
                                st.success(f"比赛已删除")
                                st.rerun()
                            except Exception as e:
                                st.error(f"删除失败：{e}")
                
                st.divider()
            
            st.caption(f"📊 总计 {len(matches_df)} 场比赛")
        else:
            st.info("暂无比赛")

# ========== 关闭数据库连接 ==========
conn.close()









