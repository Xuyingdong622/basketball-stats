import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# 页面配置
st.set_page_config(page_title="篮球数据统计", page_icon="🏀", layout="wide")

# 连接数据库
conn = sqlite3.connect('basketball.db', check_same_thread=False)

st.title("🏀 球局数据统计系统")

# 侧边栏菜单
menu = st.sidebar.selectbox("菜单", ["📝 数据录入", "📊 数据榜", "📋 比赛记录", "⚙️ 管理后台"])

# ==================== 数据录入 ====================
if menu == "📝 数据录入":
    st.header("📝 录入本场数据")
    
    # 获取所有比赛
    matches = pd.read_sql("""
        SELECT m.match_id, m.match_date, m.game_type, m.home_win, m.away_win,
               COALESCE(t1.team_name, '主队') as home_team,
               COALESCE(t2.team_name, '客队') as away_team
        FROM matches m
        LEFT JOIN teams t1 ON m.home_team_id = t1.team_id
        LEFT JOIN teams t2 ON m.away_team_id = t2.team_id
        ORDER BY m.match_date DESC
    """, conn)
    
    if matches.empty:
        st.warning("请先在管理后台添加比赛")
    else:
        # 比赛选择
        match_options = []
        game_type_display_map = {"5v5": "5v5全场", "4v4": "4v4半场抢分21", "3v3": "3v3半场抢分21"}
        for _, m in matches.iterrows():
            game_type_display = game_type_display_map.get(m['game_type'], m['game_type'])
            match_options.append(f"{m['match_date']} | {game_type_display} | {m['home_team']} vs {m['away_team']}")
        
        selected_match = st.selectbox("选择比赛", match_options, key="match_select")
        selected_idx = match_options.index(selected_match)
        match_data = matches.iloc[selected_idx]
        match_id = int(match_data['match_id'])
        
        # 显示比赛胜负设置
        st.subheader("🏆 比赛结果")
        col_win1, col_win2 = st.columns(2)
        with col_win1:
            home_win = st.checkbox(f"{match_data['home_team']} 获胜", value=bool(match_data['home_win']), key="home_win")
        with col_win2:
            away_win = st.checkbox(f"{match_data['away_team']} 获胜", value=bool(match_data['away_win']), key="away_win")
        
        # 更新比赛胜负
        if st.button("更新比赛结果", key="update_match_result"):
            conn.execute("UPDATE matches SET home_win = ?, away_win = ? WHERE match_id = ?",
                        (1 if home_win else 0, 1 if away_win else 0, match_id))
            conn.commit()
            st.success("✅ 比赛结果已更新")
            st.rerun()
        
        st.divider()
        
        # 获取所有球员
        players = pd.read_sql("SELECT player_id, player_name, team_id FROM players ORDER BY player_name", conn)
        
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
# ==================== 数据榜 ====================
elif menu == "📊 数据榜":
    st.header("📊 球员数据榜")
    
    # 刷新按钮和筛选
    col1, col2, col3, col4 = st.columns([1, 2, 2, 2])
    with col1:
        if st.button("🔄 刷新数据"):
            st.rerun()
    
    with col2:
        game_type_filter = st.selectbox(
            "🏀 比赛类型",
            ["全部", "5v5全场", "4v4半场抢分21", "3v3半场抢分21"],
            index=0,
            key="game_type_filter"
        )
    
    with col3:
        stat_type = st.selectbox(
            "📊 统计类型",
            ["综合数据", "投篮命中率", "防守数据", "胜率统计"],
            index=0,
            key="stat_type"
        )
    
    with col4:
        sort_by = st.selectbox(
            "📈 排序方式",
            ["得分", "篮板", "助攻", "抢断", "盖帽", "胜率"],
            index=0,
            key="sort_by"
        )
    
    # 转换筛选条件
    game_type_map = {
        "5v5全场": "5v5",
        "4v4半场抢分21": "4v4",
        "3v3半场抢分21": "3v3"
    }
    
    where_clause = ""
    if game_type_filter != "全部":
        game_type_code = game_type_map[game_type_filter]
        where_clause = f"AND m.game_type = '{game_type_code}'"
    
    # 查询球员统计数据（包含胜率）
    query = f"""
        SELECT 
            p.player_id,
            p.player_name,
            COUNT(DISTINCT ps.match_id) as games,
            -- 胜率计算
            SUM(CASE 
                WHEN (ps.is_home = 1 AND m.home_win = 1) OR (ps.is_home = 0 AND m.away_win = 1) 
                THEN 1 ELSE 0 END) as wins,
            -- 基础数据
            ROUND(AVG(ps.points), 1) as avg_points,
            ROUND(AVG(ps.rebounds), 1) as avg_rebounds,
            ROUND(AVG(ps.assists), 1) as avg_assists,
            ROUND(AVG(ps.steals), 1) as avg_steals,
            ROUND(AVG(ps.blocks), 1) as avg_blocks,
            ROUND(AVG(ps.turnovers), 1) as avg_turnovers,
            ROUND(AVG(ps.fouls), 1) as avg_fouls,
            -- 总计
            SUM(ps.points) as total_points,
            SUM(ps.rebounds) as total_rebounds,
            SUM(ps.assists) as total_assists,
            SUM(ps.steals) as total_steals,
            SUM(ps.blocks) as total_blocks,
            -- 投篮数据
            SUM(ps.fg2_made) as fg2m,
            SUM(ps.fg2_attempts) as fg2a,
            SUM(ps.fg3_made) as fg3m,
            SUM(ps.fg3_attempts) as fg3a,
            SUM(ps.ft_made) as ftm,
            SUM(ps.ft_attempts) as fta
        FROM player_stats ps
        JOIN players p ON ps.player_id = p.player_id
        JOIN matches m ON ps.match_id = m.match_id
        WHERE 1=1 {where_clause}
        GROUP BY p.player_id
    """
    
    try:
        df = pd.read_sql(query, conn)
        
        if not df.empty:
            # 计算命中率和胜率
            df['fg2_pct'] = df.apply(lambda x: round(x['fg2m']/x['fg2a']*100, 1) if x['fg2a'] > 0 else 0, axis=1)
            df['fg3_pct'] = df.apply(lambda x: round(x['fg3m']/x['fg3a']*100, 1) if x['fg3a'] > 0 else 0, axis=1)
            df['ft_pct'] = df.apply(lambda x: round(x['ftm']/x['fta']*100, 1) if x['fta'] > 0 else 0, axis=1)
            df['win_rate'] = df.apply(lambda x: round(x['wins']/x['games']*100, 1) if x['games'] > 0 else 0, axis=1)
            
            # 根据排序方式排序
            sort_map = {
                "得分": "avg_points",
                "篮板": "avg_rebounds", 
                "助攻": "avg_assists",
                "抢断": "avg_steals",
                "盖帽": "avg_blocks",
                "胜率": "win_rate"
            }
            df = df.sort_values(by=sort_map[sort_by], ascending=False)
            
            # 显示当前筛选条件
            if game_type_filter != "全部":
                st.info(f"🏀 当前筛选：{game_type_filter}")
            
            if stat_type == "综合数据":
                st.subheader("📊 综合数据")
                display_df = df[['player_name', 'games', 'wins', 'win_rate', 'avg_points', 'avg_rebounds', 
                                 'avg_assists', 'avg_steals', 'avg_blocks', 'avg_turnovers', 'avg_fouls']].copy()
                display_df.columns = ['球员', '场次', '胜场', '胜率%', '得分', '篮板', 
                                      '助攻', '抢断', '盖帽', '失误', '犯规']
                st.dataframe(display_df, use_container_width=True)
                
            elif stat_type == "投篮命中率":
                st.subheader("🏹 投篮命中率")
                display_df = df[['player_name', 'games', 'fg2_pct', 'fg3_pct', 'ft_pct', 
                                 'fg2m', 'fg2a', 'fg3m', 'fg3a', 'ftm', 'fta']].copy()
                display_df.columns = ['球员', '场次', '两分%', '三分%', '罚球%', 
                                      '两中', '两投', '三中', '三投', '罚中', '罚投']
                st.dataframe(display_df, use_container_width=True)
                
            elif stat_type == "防守数据":
                st.subheader("🛡️ 防守数据")
                display_df = df[['player_name', 'games', 'avg_rebounds', 'avg_steals', 'avg_blocks',
                                 'total_rebounds', 'total_steals', 'total_blocks']].copy()
                display_df.columns = ['球员', '场次', '篮板', '抢断', '盖帽', 
                                      '总篮板', '总抢断', '总盖帽']
                st.dataframe(display_df, use_container_width=True)
                
            else:  # 胜率统计
                st.subheader("🏆 胜率统计")
                display_df = df[['player_name', 'games', 'wins', 'win_rate', 'avg_points', 
                                 'avg_rebounds', 'avg_assists']].copy()
                display_df.columns = ['球员', '场次', '胜场', '胜率%', '场均得分', '场均篮板', '场均助攻']
                st.dataframe(display_df, use_container_width=True)
            
            # 统计信息
            st.caption(f"📊 总计 {len(df)} 名球员，共 {df['games'].sum()} 场比赛")
            
        else:
            st.warning("暂无数据，请先录入比赛数据")
            
    except Exception as e:
        st.error(f"查询出错：{e}")
# ==================== 比赛记录 ====================
elif menu == "📋 比赛记录":
    st.header("📋 比赛记录")
    
    # 查询所有比赛
    matches = pd.read_sql("""
        SELECT m.match_id, m.match_date, m.game_type, m.home_win, m.away_win,
               COALESCE(t1.team_name, '主队') as home_team,
               COALESCE(t2.team_name, '客队') as away_team
        FROM matches m
        LEFT JOIN teams t1 ON m.home_team_id = t1.team_id
        LEFT JOIN teams t2 ON m.away_team_id = t2.team_id
        ORDER BY m.match_date DESC
    """, conn)
    
    game_type_display_map = {"5v5": "5v5全场", "4v4": "4v4半场抢分21", "3v3": "3v3半场抢分21"}
    
    for _, m in matches.iterrows():
        game_type_display = game_type_display_map.get(m['game_type'], m['game_type'])
        
        # 查询本场比赛的球员数据（用于显示预览）
        stats_df = pd.read_sql(f"""
            SELECT 
                p.player_name,
                CASE WHEN ps.is_home = 1 THEN '{m['home_team']}' ELSE '{m['away_team']}' END as team,
                ps.points
            FROM player_stats ps
            JOIN players p ON ps.player_id = p.player_id
            WHERE ps.match_id = {m['match_id']}
            ORDER BY ps.points DESC
        """, conn)
        
        # 计算两队总得分和球员名单
        home_players = []
        away_players = []
        home_total = 0
        away_total = 0
        
        if not stats_df.empty:
            home_stats = stats_df[stats_df['team'] == m['home_team']]
            away_stats = stats_df[stats_df['team'] == m['away_team']]
            
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
        preview_text = f"{m['match_date']} [{game_type_display}] {m['home_team']} {home_total} : {away_total} {m['away_team']}"
        if winner:
            preview_text += f" {winner}"
        
        # 添加球员预览
        if home_players or away_players:
            preview_text += "\n\n"
            if home_players:
                preview_text += f"👥 {m['home_team']}: {', '.join(home_players[:3])}"
                if len(home_players) > 3:
                    preview_text += f" 等{len(home_players)}人"
            preview_text += "\n"
            if away_players:
                preview_text += f"👥 {m['away_team']}: {', '.join(away_players[:3])}"
                if len(away_players) > 3:
                    preview_text += f" 等{len(away_players)}人"
        
        with st.expander(preview_text):
            # 重新查询完整数据用于展开显示
            full_stats_df = pd.read_sql(f"""
                SELECT 
                    ps.stat_id,
                    p.player_name,
                    CASE WHEN ps.is_home = 1 THEN '{m['home_team']}' ELSE '{m['away_team']}' END as team,
                    ps.points,
                    ps.rebounds,
                    ps.assists,
                    ps.steals,
                    ps.blocks,
                    ps.turnovers,
                    ps.fouls,
                    ps.fg2_made || '/' || ps.fg2_attempts as fg2,
                    ps.fg3_made || '/' || ps.fg3_attempts as fg3,
                    ps.ft_made || '/' || ps.ft_attempts as ft
                FROM player_stats ps
                JOIN players p ON ps.player_id = p.player_id
                WHERE ps.match_id = {m['match_id']}
                ORDER BY ps.points DESC
            """, conn)
            
            if not full_stats_df.empty:
                # 显示两队总得分
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric(f"{m['home_team']} 总得分", home_total)
                with col2:
                    st.metric(f"{m['away_team']} 总得分", away_total)
                with col3:
                    st.metric("分差", abs(home_total - away_total))
                
                st.divider()
                
                # 显示表头
                col_a, col_b, col_c, col_d, col_e, col_f, col_g, col_h, col_i, col_j, col_k = st.columns([1.5, 1, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 2, 0.5])
                with col_a:
                    st.write("**球员**")
                with col_b:
                    st.write("**队伍**")
                with col_c:
                    st.write("**得分**")
                with col_d:
                    st.write("**篮板**")
                with col_e:
                    st.write("**助攻**")
                with col_f:
                    st.write("**抢断**")
                with col_g:
                    st.write("**盖帽**")
                with col_h:
                    st.write("**失误**")
                with col_i:
                    st.write("**犯规**")
                with col_j:
                    st.write("**投篮**")
                with col_k:
                    st.write("**操作**")
                
                st.divider()
                
                # 显示球员数据表格，每行带删除按钮
                for idx, row_stat in full_stats_df.iterrows():
                    col_a, col_b, col_c, col_d, col_e, col_f, col_g, col_h, col_i, col_j, col_k = st.columns([1.5, 1, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 2, 0.5])
                    
                    with col_a:
                        st.write(f"{row_stat['player_name']}")
                    with col_b:
                        st.write(f"{row_stat['team']}")
                    with col_c:
                        st.write(f"{row_stat['points']}")
                    with col_d:
                        st.write(f"{row_stat['rebounds']}")
                    with col_e:
                        st.write(f"{row_stat['assists']}")
                    with col_f:
                        st.write(f"{row_stat['steals']}")
                    with col_g:
                        st.write(f"{row_stat['blocks']}")
                    with col_h:
                        st.write(f"{row_stat['turnovers']}")
                    with col_i:
                        st.write(f"{row_stat['fouls']}")
                    with col_j:
                        st.write(f"{row_stat['fg2']} | {row_stat['fg3']} | {row_stat['ft']}")
                    with col_k:
                        # 删除单条数据按钮
                        if st.button("🗑️", key=f"del_stat_{row_stat['stat_id']}", help="删除这条数据"):
                            try:
                                conn.execute("DELETE FROM player_stats WHERE stat_id = ?", (row_stat['stat_id'],))
                                conn.commit()
                                st.success(f"✅ 已删除 {row_stat['player_name']} 的数据")
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ 删除失败：{e}")
                    
                    st.divider()
                
                st.caption(f"本场共 {len(full_stats_df)} 名球员")
            else:
                st.info("暂无球员数据")# ==================== 管理后台 ====================
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
            match_date = st.date_input("比赛日期")
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
                            INSERT INTO matches (match_date, game_type, home_team_id, away_team_id)
                            VALUES (?, ?, ?, ?)
                        """, (match_date, game_type, home_team, away_team))
                        conn.commit()
                        st.success("比赛创建成功")
                        st.rerun()
                    except Exception as e:
                        st.error(f"创建失败：{e}")
        
        st.divider()
        st.subheader("现有比赛")
        
        # 查询所有比赛
        matches_df = pd.read_sql("""
            SELECT 
                m.match_id,
                m.match_date,
                m.game_type,
                COALESCE(t1.team_name, '主队') as home_team,
                COALESCE(t2.team_name, '客队') as away_team,
                m.home_win,
                m.away_win,
                COUNT(ps.stat_id) as stats_count
            FROM matches m
            LEFT JOIN teams t1 ON m.home_team_id = t1.team_id
            LEFT JOIN teams t2 ON m.away_team_id = t2.team_id
            LEFT JOIN player_stats ps ON m.match_id = ps.match_id
            GROUP BY m.match_id
            ORDER BY m.match_date DESC
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
                    st.write(f"{game_type_display}")
                
                with col3:
                    st.write(f"{row['home_team']} vs {row['away_team']}")
                
                with col4:
                    if winner:
                        st.write(f"{winner}")
                    else:
                        st.write("未设置胜负")
                
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
            
            st.caption(f"总计 {len(matches_df)} 场比赛")
        else:
            st.info("暂无比赛")