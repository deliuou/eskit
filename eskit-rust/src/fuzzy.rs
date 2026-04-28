use crate::util::basename;

pub fn fuzzy_match_score(query: &str, path: &str) -> Option<i32> {
    let q = query.trim().to_ascii_lowercase();
    if q.is_empty() || q == "*" {
        return Some(0);
    }
    let name = basename(path);
    let lower = name.to_ascii_lowercase();
    if lower.contains(&q) {
        return Some(1000 - lower.find(&q).unwrap_or(0) as i32);
    }
    let ascii = ascii_squash(&lower);
    if ascii.contains(&q) {
        return Some(850 - ascii.find(&q).unwrap_or(0) as i32);
    }
    let initials = initials(&name);
    if initials.contains(&q) {
        return Some(750 - initials.find(&q).unwrap_or(0) as i32);
    }
    if is_subsequence(&q, &lower) {
        return Some(500 - lower.len() as i32);
    }
    if is_subsequence(&q, &initials) {
        return Some(450 - initials.len() as i32);
    }
    None
}

pub fn sort_paths_listary(query: &str, paths: Vec<String>) -> Vec<String> {
    let mut scored: Vec<(i32, usize, String)> = paths
        .into_iter()
        .enumerate()
        .filter_map(|(i, p)| fuzzy_match_score(query, &p).map(|score| (score, i, p)))
        .collect();
    scored.sort_by(|a, b| b.0.cmp(&a.0).then_with(|| a.1.cmp(&b.1)));
    scored.into_iter().map(|(_, _, p)| p).collect()
}

fn is_subsequence(q: &str, text: &str) -> bool {
    let mut it = text.chars();
    for ch in q.chars() {
        if !it.any(|t| t == ch) {
            return false;
        }
    }
    true
}

fn ascii_squash(text: &str) -> String {
    text.chars().filter(|c| c.is_ascii_alphanumeric()).collect()
}

fn initials(text: &str) -> String {
    let mut out = String::new();
    let mut new_word = true;
    for ch in text.chars() {
        if ch.is_ascii_alphanumeric() {
            if new_word {
                out.push(ch.to_ascii_lowercase());
                new_word = false;
            }
        } else {
            new_word = true;
        }
        if let Some(py) = common_chinese_initial(ch) {
            out.push(py);
            new_word = true;
        }
    }
    out
}

fn common_chinese_initial(ch: char) -> Option<char> {
    // Lightweight fallback for common daily filenames.  It is not a full pinyin
    // library, but it covers the most common terms used in examples and keeps
    // the Rust binary small and dependency-light.
    Some(match ch {
        '欧' => 'o', '得' => 'd', '柳' => 'l',
        '开' => 'k', '题' => 't', '报' => 'b', '告' => 'g',
        '论' => 'l', '文' => 'w', '图' => 't', '片' => 'p',
        '截' => 'j', '屏' => 'p', '照' => 'z', '相' => 'x',
        '项' => 'x', '目' => 'm', '数' => 's', '据' => 'j',
        '代' => 'd', '码' => 'm', '测' => 'c', '试' => 's',
        '下' => 'x', '载' => 'z', '桌' => 'z', '面' => 'm',
        '备' => 'b', '份' => 'f', '新' => 'x', '旧' => 'j',
        '空' => 'k', '文' => 'w', '件' => 'j', '夹' => 'j',
        '目' => 'm', '录' => 'l', '课' => 'k', '件' => 'j',
        '幻' => 'h', '灯' => 'd', '汇' => 'h', '报' => 'b',
        '笔' => 'b', '记' => 'j', '材' => 'c', '料' => 'l',
        '安' => 'a', '装' => 'z', '说' => 's', '明' => 'm',
        '搜' => 's', '索' => 's', '结' => 'j', '果' => 'g',
        _ => return None,
    })
}
