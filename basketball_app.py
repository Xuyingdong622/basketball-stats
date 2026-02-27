import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from supabase import create_client, Client

# ========== 页面配置 ==========
st.set_page_config(page_title="小东瓜数据统计系统", page_icon="🏀", layout="wide")

# ========== 初始化 Supabase 连接 ==========
@st.cache_resource
def init_supabase():
    """初始化 Supabase 客户端"""
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

# ========== 数据查询函数（带缓存） ==========
@st.cache_data(ttl=60)
def get_players():
    """获取所有球员"""
    response = supabase.table("players").select("*").order("player_name").execute()
    return pd.DataFrame(response.data) if response.data else pd.DataFrame()

@st.cache_data(ttl=60)
def get_teams():
    """获取所有球队"""
    response = supabase.table("teams").select("*").order("team_name").execute()
    return pd.DataFrame(response.data) if response.data else pd.DataFrame()

@st.cache_data(ttl=60)
def get_matches():
    """获取所有比赛"""
    response = supabase.table("matches").select("*").order("match_date", desc=True).order("match_name").execute()
    return pd.DataFrame(response.data) if response.data else pd.DataFrame()

@st.cache_data(ttl=60)
def get_player_stats(match_id=None):
    """获取球员统计数据，可按比赛筛选"""
    query = supabase.table("player_stats").select("*")
    if match_id:
        query = query.eq("match_id", match_id)
    response = query.execute()
    return pd.DataFrame(response.data) if response.data else pd.DataFrame()

# ========== 清除缓存 ==========
def clear_cache():
    """清除所有缓存，确保数据实时更新"""
    st.cache_data.clear()

# ========== 主页面标题 ==========
st.title("🏀 小东瓜数据统计系统")

# ========== 侧边栏菜单 ==========
menu = st.sidebar.selectbox("菜单", ["📊 球员数据榜", "📋 比赛记录", "📝 数据录入", "⚙️ 管理后台"])

# ========== 侧边栏装饰 ==========
st.sidebar.markdown("---")
st.sidebar.markdown("🏀 记录每一刻精彩")

# ==================== 数据录入 ====================
if menu == "📝 数据录入":
    st.header("📝 录入本场数据")
    
    # 获取比赛数据
    matches_df = get_matches()
    
    if matches_df.empty:
        st.warning("请先在管理后台添加比赛")
    else:
        # 获取球队信息用于显示队伍名称
        teams_df = get_teams()
        
        # 构建比赛选项
        match_options = []
        game_type_display_map = {"5v5": "5v5全场", "4v4": "4v4半场抢分21", "3v3": "3v3半场抢分21"}
        
        for _, row in matches_df.iterrows():
            # 获取队伍名称
            home_team_name = "队伍1"
            away_team_name = "队伍2"
            
            if pd.notna(row['home_team_id']) and row['home_team_id'] is not None:
                home_team = teams_df[teams_df['team_id'] == row['home_team_id']]
                if not home_team.empty:
                    home_team_name = home_team.iloc[0]['team_name']
            
            if pd.notna(row['away_team_id']) and row['away_team_id'] is not None:
                away_team = teams_df[teams_df['team_id'] == row['away_team_id']]
                if not away_team.empty:
                    away_team_name = away_team.iloc[0]['team_name']
            
            game_type_display = game_type_display_map.get(row['game_type'], row['game_type'])
            match_options.append(f"{row['match_date']} {row['match_name']} | {game_type_display} | {home_team_name} vs {away_team_name}")
        
        selected_match = st.selectbox("选择比赛", match_options, key="match_select")
        selected_idx = match_options.index(selected_match)
        match_data = matches_df.iloc[selected_idx]
        match_id = int(match_data['match_id'])
        
        # 获取当前比赛的队伍名称
        current_home_team = "队伍1"
        current_away_team = "队伍2"
        
        if pd.notna(match_data['home_team_id']) and match_data['home_team_id'] is not None:
            home_team = teams_df[teams_df['team_id'] == match_data['home_team_id']]
            if not home_team.empty:
                current_home_team = home_team.iloc[0]['team_name']
        
        if pd.notna(match_data['away_team_id']) and match_data['away_team_id'] is not None:
            away_team = teams_df[teams_df['team_id'] == match_data['away_team_id']]
            if not away_team.empty:
                current_away_team = away_team.iloc[0]['team_name']
        
        st.divider()
        
        # 获取所有球员
        players_df = get_players()
        
        if players_df.empty:
            st.warning("请先在管理后台添加球员")
        else:
            # 球员选择
            selected_player = st.selectbox(
                "选择球员", 
                players_df['player_id'].tolist(),
                format_func=lambda x: players_df[players_df['player_id'] == x]['player_name'].values[0],
                key="player_select"
            )
            
            # 主客队选择
            is_home = st.radio(
                "球员所在队伍",
                [f"🏠 {current_home_team}", f"✈️ {current_away_team}"],
                horizontal=True,
                key="home_away"
            )
            is_home_value = 1 if "🏠" in is_home else 0
            
            # 检查是否已有该球员本场比赛的数据
            stats_df = get_player_stats(match_id)
            existing_data = stats_df[stats_df['player_id'] == selected_player]
            
            default_values = None
            if not existing_data.empty:
                default_values = existing_data.iloc[0].to_dict()
                st.warning("⚠️ 该球员本场比赛已有数据，将进行更新")
                st.info(f"当前数据：得分 {default_values['points']}分，篮板 {default_values['rebounds']}个")
            else:
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
                    # 准备数据
                    stats_data = {
                        "player_id": int(selected_player),
                        "match_id": match_id,
                        "points": total_points,
                        "rebounds": rebounds,
                        "assists": assists,
                        "steals": steals,
                        "blocks": blocks,
                        "turnovers": turnovers,
                        "fouls": fouls,
                        "fg2_made": fg2_m,
                        "fg2_attempts": fg2_a,
                        "fg3_made": fg3_m,
                        "fg3_attempts": fg3_a,
                        "ft_made": ft_m,
                        "ft_attempts": ft_a,
                        "is_home": is_home_value
                    }
                    
                    if not existing_data.empty:
                        # 更新现有数据
                        stat_id = existing_data.iloc[0]['stat_id']
                        supabase.table("player_stats").update(stats_data).eq("stat_id", stat_id).execute()
                    else:
                        # 插入新数据
                        supabase.table("player_stats").insert(stats_data).execute()
                    
                    # ===== 更新该场比赛的总分和胜负 =====
                    # 获取该场比赛所有球员数据
                    all_stats = supabase.table("player_stats").select("*").eq("match_id", match_id).execute()
                    stats_list = all_stats.data
                    
                    home_total = 0
                    away_total = 0
                    
                    for stat in stats_list:
                        if stat['is_home'] == 1:
                            home_total += stat['points']
                        else:
                            away_total += stat['points']
                    
                    # 更新比赛总分
                    match_update = {
                        "home_manual_score": home_total,
                        "away_manual_score": away_total
                    }
                    
                    # 判断胜负
                    if home_total > away_total:
                        match_update["home_win"] = 1
                        match_update["away_win"] = 0
                    elif away_total > home_total:
                        match_update["home_win"] = 0
                        match_update["away_win"] = 1
                    else:
                        match_update["home_win"] = 0
                        match_update["away_win"] = 0
                    
                    supabase.table("matches").update(match_update).eq("match_id", match_id).execute()
                    
                    # 清除缓存
                    clear_cache()
                    
                    st.success("✅ 数据保存成功！")
                    st.balloons()
                    
                except Exception as e:
                    st.error(f"❌ 保存失败：{str(e)}")

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
    
    # 获取所有数据
    players_df = get_players()
    matches_df = get_matches()
    stats_df = get_player_stats()
    
    if stats_df.empty:
        st.warning("暂无数据，请先录入比赛数据")
    else:
        # 合并数据
        merged_df = stats_df.merge(players_df, on='player_id', how='left')
        merged_df = merged_df.merge(matches_df, on='match_id', how='left')
        
        # 应用比赛类型筛选
        if game_type_filter != "全部":
            game_type_map = {
                "5v5全场": "5v5",
                "4v4半场抢分21": "4v4",
                "3v3半场抢分21": "3v3"
            }
            game_type_code = game_type_map[game_type_filter]
            merged_df = merged_df[merged_df['game_type'] == game_type_code]
        
        if merged_df.empty:
            st.warning(f"暂无 {game_type_filter} 类型的数据")
        else:
            # 计算每个球员的统计数据
            player_stats = merged_df.groupby(['player_id', 'player_name']).agg({
                'match_id': 'nunique',
                'points': ['sum', 'mean'],
                'rebounds': ['sum', 'mean'],
                'assists': ['sum', 'mean'],
                'steals': ['sum', 'mean'],
                'blocks': ['sum', 'mean'],
                'turnovers': ['sum', 'mean'],
                'fouls': ['sum', 'mean'],
                'fg2_made': 'sum',
                'fg2_attempts': 'sum',
                'fg3_made': 'sum',
                'fg3_attempts': 'sum',
                'ft_made': 'sum',
                'ft_attempts': 'sum'
            }).round(1)
            
            # 重命名列
            player_stats.columns = ['games', 'total_points', 'avg_points',
                                    'total_rebounds', 'avg_rebounds',
                                    'total_assists', 'avg_assists',
                                    'total_steals', 'avg_steals',
                                    'total_blocks', 'avg_blocks',
                                    'total_turnovers', 'avg_turnovers',
                                    'total_fouls', 'avg_fouls',
                                    'total_fg2_made', 'total_fg2_att',
                                    'total_fg3_made', 'total_fg3_att',
                                    'total_ft_made', 'total_ft_att']
            
            player_stats = player_stats.reset_index()
            
            # 计算命中率
            player_stats['fg2_pct'] = (player_stats['total_fg2_made'] / player_stats['total_fg2_att'] * 100).round(1)
            player_stats['fg3_pct'] = (player_stats['total_fg3_made'] / player_stats['total_fg3_att'] * 100).round(1)
            player_stats['ft_pct'] = (player_stats['total_ft_made'] / player_stats['total_ft_att'] * 100).round(1)
            
            # 计算胜率
            match_results = merged_df[['match_id', 'player_id', 'is_home', 'home_win', 'away_win']].drop_duplicates()
            match_results['win'] = ((match_results['is_home'] == 1) & (match_results['home_win'] == 1)) | \
                                   ((match_results['is_home'] == 0) & (match_results['away_win'] == 1))
            
            wins = match_results.groupby('player_id')['win'].sum().reset_index()
            wins.columns = ['player_id', 'wins']
            
            player_stats = player_stats.merge(wins, on='player_id', how='left')
            player_stats['wins'] = player_stats['wins'].fillna(0)
            player_stats['win_rate'] = (player_stats['wins'] / player_stats['games'] * 100).round(1)
            
            # 场均数据表格
            st.subheader("📈 场均数据")
            avg_display = player_stats[['player_name', 'games', 'wins', 'win_rate',
                                        'avg_points', 'avg_rebounds', 'avg_assists',
                                        'avg_steals', 'avg_blocks', 'avg_turnovers', 'avg_fouls',
                                        'fg2_pct', 'fg3_pct', 'ft_pct']].copy()
            
            avg_display.columns = ['球员', '场次', '胜场', '胜率%',
                                   '得分', '篮板', '助攻', '抢断', '盖帽', '失误', '犯规',
                                   '两分%', '三分%', '罚球%']
            
            st.dataframe(avg_display, use_container_width=True)
            
            st.divider()
            
            # 总数数据表格
            st.subheader("📊 总数数据")
            total_display = player_stats[['player_name', 'games', 'wins', 'win_rate',
                                          'total_points', 'total_rebounds', 'total_assists',
                                          'total_steals', 'total_blocks', 'total_turnovers', 'total_fouls',
                                          'total_fg2_made', 'total_fg2_att',
                                          'total_fg3_made', 'total_fg3_att',
                                          'total_ft_made', 'total_ft_att',
                                          'fg2_pct', 'fg3_pct', 'ft_pct']].copy()
            
            total_display.columns = ['球员', '场次', '胜场', '胜率%',
                                     '总得分', '总篮板', '总助攻', '总抢断', '总盖帽',
                                     '总失误', '总犯规',
                                     '两分中', '两分投', '三分中', '三分投',
                                     '罚球中', '罚球投', '两分%', '三分%', '罚球%']
            
            st.dataframe(total_display, use_container_width=True)
            
            # 统计信息
            st.caption(f"📊 总计 {len(player_stats)} 名球员，共 {player_stats['games'].sum()} 场比赛")
            
            # 各项数据王
            st.subheader("🏆 场均数据王")
            
            if len(player_stats) > 0:
                top_scorer = player_stats.loc[player_stats['avg_points'].idxmax()]
                top_rebounder = player_stats.loc[player_stats['avg_rebounds'].idxmax()]
                top_assister = player_stats.loc[player_stats['avg_assists'].idxmax()]
                top_stealer = player_stats.loc[player_stats['avg_steals'].idxmax()]
                top_blocker = player_stats.loc[player_stats['avg_blocks'].idxmax()]
                
                col1, col2, col3, col4, col5 = st.columns(5)
                
                with col1:
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                                padding: 15px; border-radius: 10px; text-align: center;">
                        <h3 style="color: white; margin: 0; font-size: 1.2rem;">🏀 得分王</h3>
                        <p style="color: white; font-size: 1.5rem; margin: 5px 0; font-weight: bold;">
                            {top_scorer['avg_points']:.1f}
                        </p>
                        <p style="color: white; margin: 0; font-size: 1rem;">{top_scorer['player_name']}</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                                padding: 15px; border-radius: 10px; text-align: center;">
                        <h3 style="color: white; margin: 0; font-size: 1.2rem;">📊 篮板王</h3>
                        <p style="color: white; font-size: 1.5rem; margin: 5px 0; font-weight: bold;">
                            {top_rebounder['avg_rebounds']:.1f}
                        </p>
                        <p style="color: white; margin: 0; font-size: 1rem;">{top_rebounder['player_name']}</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col3:
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                                padding: 15px; border-radius: 10px; text-align: center;">
                        <h3 style="color: white; margin: 0; font-size: 1.2rem;">🎯 助攻王</h3>
                        <p style="color: white; font-size: 1.5rem; margin: 5px 0; font-weight: bold;">
                            {top_assister['avg_assists']:.1f}
                        </p>
                        <p style="color: white; margin: 0; font-size: 1rem;">{top_assister['player_name']}</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col4:
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                                padding: 15px; border-radius: 10px; text-align: center;">
                        <h3 style="color: white; margin: 0; font-size: 1.2rem;">✋ 抢断王</h3>
                        <p style="color: white; font-size: 1.5rem; margin: 5px 0; font-weight: bold;">
                            {top_stealer['avg_steals']:.1f}
                        </p>
                        <p style="color: white; margin: 0; font-size: 1rem;">{top_stealer['player_name']}</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col5:
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                                padding: 15px; border-radius: 10px; text-align: center;">
                        <h3 style="color: white; margin: 0; font-size: 1.2rem;">🛡️ 盖帽王</h3>
                        <p style="color: white; font-size: 1.5rem; margin: 5px 0; font-weight: bold;">
                            {top_blocker['avg_blocks']:.1f}
                        </p>
                        <p style="color: white; margin: 0; font-size: 1rem;">{top_blocker['player_name']}</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                # 胜率王
                top_winner = player_stats.loc[player_stats['win_rate'].idxmax()]
                st.info(f"🏆 胜率王：**{top_winner['player_name']}** {top_winner['win_rate']}% ({top_winner['wins']}胜/{top_winner['games']}场)")

# ==================== 比赛记录 ====================
elif menu == "📋 比赛记录":
    st.header("📋 比赛记录")
    
    # 获取数据
    matches_df = get_matches()
    teams_df = get_teams()
    players_df = get_players()
    stats_df = get_player_stats()
    
    game_type_display_map = {"5v5": "5v5全场", "4v4": "4v4半场抢分21", "3v3": "3v3半场抢分21"}
    
    for _, match in matches_df.iterrows():
        # 获取队伍名称
        home_team_name = "队伍1"
        away_team_name = "队伍2"
        
        if pd.notna(match['home_team_id']) and match['home_team_id'] is not None:
            home_team = teams_df[teams_df['team_id'] == match['home_team_id']]
            if not home_team.empty:
                home_team_name = home_team.iloc[0]['team_name']
        
        if pd.notna(match['away_team_id']) and match['away_team_id'] is not None:
            away_team = teams_df[teams_df['team_id'] == match['away_team_id']]
            if not away_team.empty:
                away_team_name = away_team.iloc[0]['team_name']
        
        game_type_display = game_type_display_map.get(match['game_type'], match['game_type'])
        
        # 获取本场比赛的球员数据
        match_stats = stats_df[stats_df['match_id'] == match['match_id']].copy()
        
        # 计算两队总得分
        home_total = 0
        away_total = 0
        home_players = []
        away_players = []
        
        if not match_stats.empty:
            home_stats = match_stats[match_stats['is_home'] == 1]
            away_stats = match_stats[match_stats['is_home'] == 0]
            
            home_players = home_stats.merge(players_df, on='player_id')['player_name'].tolist()
            away_players = away_stats.merge(players_df, on='player_id')['player_name'].tolist()
            
            home_total = home_stats['points'].sum() if not home_stats.empty else 0
            away_total = away_stats['points'].sum() if not away_stats.empty else 0
        
        # 确定获胜方
        winner = ""
        if home_total > away_total:
            winner = f"🏆 {home_team_name} 获胜"
        elif away_total > home_total:
            winner = f"🏆 {away_team_name} 获胜"
        elif home_total > 0 and home_total == away_total:
            winner = "🤝 平局"
        
        # 创建预览文本
        preview_text = f"📅 {match['match_date']} {match['match_name']} [{game_type_display}]"
        preview_text += f"\n{home_team_name} {home_total} : {away_total} {away_team_name}"
        if winner:
            preview_text += f"  {winner}"
        
        # 添加球员预览
        if home_players or away_players:
            preview_text += "\n\n"
            if home_players:
                preview_text += f"🏠 {home_team_name}: {', '.join(home_players[:3])}"
                if len(home_players) > 3:
                    preview_text += f" 等{len(home_players)}人"
            preview_text += "\n"
            if away_players:
                preview_text += f"✈️ {away_team_name}: {', '.join(away_players[:3])}"
                if len(away_players) > 3:
                    preview_text += f" 等{len(away_players)}人"
        
        with st.expander(preview_text):
            if not match_stats.empty:
                # 显示比分
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric(f"{home_team_name} 总得分", home_total)
                with col2:
                    st.metric(f"{away_team_name} 总得分", away_total)
                with col3:
                    st.metric("分差", abs(home_total - away_total))
                
                st.markdown("---")
                
                # 分离主客队数据
                home_stats = match_stats[match_stats['is_home'] == 1].copy()
                away_stats = match_stats[match_stats['is_home'] == 0].copy()
                
                # 主队数据表格
                if not home_stats.empty:
                    st.subheader(f"🏠 {home_team_name}")
                    
                    home_display = home_stats.merge(players_df, on='player_id')
                    home_display = home_display[['player_name', 'points', 'rebounds', 'assists',
                                                  'steals', 'blocks', 'turnovers', 'fouls']]
                    home_display.columns = ['球员', '得分', '篮板', '助攻', '抢断', '盖帽', '失误', '犯规']
                    st.dataframe(home_display, use_container_width=True, hide_index=True)
                else:
                    st.info(f"{home_team_name} 暂无球员数据")
                
                st.markdown("---")
                
                # 客队数据表格
                if not away_stats.empty:
                    st.subheader(f"✈️ {away_team_name}")
                    
                    away_display = away_stats.merge(players_df, on='player_id')
                    away_display = away_display[['player_name', 'points', 'rebounds', 'assists',
                                                  'steals', 'blocks', 'turnovers', 'fouls']]
                    away_display.columns = ['球员', '得分', '篮板', '助攻', '抢断', '盖帽', '失误', '犯规']
                    st.dataframe(away_display, use_container_width=True, hide_index=True)
                else:
                    st.info(f"{away_team_name} 暂无球员数据")
                
                st.caption(f"本场共 {len(match_stats)} 名球员")
            else:
                st.info("暂无球员数据")

# ==================== 管理后台 ====================
elif menu == "⚙️ 管理后台":
    st.header("⚙️ 管理后台")
    
    # 创建三个标签页（移除了备份管理，因为数据永久保存了）
    tab1, tab2, tab3 = st.tabs(["🏀 球队管理", "👤 球员管理", "📅 比赛管理"])
    
    # ========== 球队管理 ==========
    with tab1:
        st.subheader("添加球队")
        with st.form("add_team_form"):
            team_name = st.text_input("球队名称")
            if st.form_submit_button("添加球队"):
                if team_name:
                    try:
                        data = {"team_name": team_name}
                        supabase.table("teams").insert(data).execute()
                        clear_cache()
                        st.success(f"✅ 球队 {team_name} 添加成功")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ 添加失败：{e}")
        
        st.divider()
        st.subheader("现有球队")
        
        teams_df = get_teams()
        players_df = get_players()
        
        if not teams_df.empty:
            for _, row in teams_df.iterrows():
                player_count = len(players_df[players_df['team_id'] == row['team_id']])
                
                col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                
                with col1:
                    st.write(f"**{row['team_name']}**")
                
                with col2:
                    st.write(f"{row['created_date']}")
                
                with col3:
                    st.write(f"{player_count} 名球员")
                
                with col4:
                    if st.button("🗑️", key=f"del_team_{row['team_id']}", help="删除球队"):
                        if player_count > 0:
                            st.warning(f"该球队有 {player_count} 名球员，无法删除")
                        else:
                            try:
                                supabase.table("teams").delete().eq("team_id", row['team_id']).execute()
                                clear_cache()
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
                        data = {
                            "player_name": player_name,
                            "jersey_number": jersey
                        }
                        supabase.table("players").insert(data).execute()
                        clear_cache()
                        st.success(f"球员 {player_name} 添加成功")
                        st.rerun()
                    except Exception as e:
                        st.error(f"添加失败：{e}")
        
        st.divider()
        st.subheader("现有球员")
        
        players_df = get_players()
        stats_df = get_player_stats()
        
        if not players_df.empty:
            for _, row in players_df.iterrows():
                stats_count = len(stats_df[stats_df['player_id'] == row['player_id']])
                
                col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                
                with col1:
                    st.write(f"**{row['player_name']}**")
                
                with col2:
                    st.write(f"#{row['jersey_number']}")
                
                with col3:
                    st.write(f"{stats_count} 条记录")
                
                with col4:
                    if st.button("🗑️", key=f"del_player_{row['player_id']}", help="删除球员"):
                        if stats_count > 0:
                            st.warning(f"该球员有 {stats_count} 条比赛记录，无法删除")
                        else:
                            try:
                                supabase.table("players").delete().eq("player_id", row['player_id']).execute()
                                clear_cache()
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
            
            teams_df = get_teams()
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
                        data = {
                            "match_date": str(match_date),
                            "match_name": match_name,
                            "game_type": game_type,
                            "home_team_id": home_team,
                            "away_team_id": away_team,
                            "home_manual_score": 0,
                            "away_manual_score": 0,
                            "home_win": 0,
                            "away_win": 0
                        }
                        supabase.table("matches").insert(data).execute()
                        clear_cache()
                        st.success(f"✅ 比赛创建成功：{match_date} {match_name}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ 创建失败：{e}")
