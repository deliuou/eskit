use std::io::{stdout, Write};

use crossterm::{
    cursor::{Hide, MoveTo, Show},
    event::{self, Event, KeyCode},
    execute, queue,
    style::{Attribute, Print, SetAttribute},
    terminal::{self, Clear, ClearType, EnterAlternateScreen, LeaveAlternateScreen},
};

use crate::actions::{run_action, ActionKind};
use crate::formatters::{format_size, format_time};
use crate::models::SearchResult;
use crate::util::basename;

struct TerminalGuard;
impl TerminalGuard {
    fn enter() -> std::io::Result<Self> {
        terminal::enable_raw_mode()?;
        execute!(stdout(), EnterAlternateScreen, Hide)?;
        Ok(Self)
    }
}
impl Drop for TerminalGuard {
    fn drop(&mut self) {
        let _ = execute!(stdout(), Show, LeaveAlternateScreen);
        let _ = terminal::disable_raw_mode();
    }
}

pub fn select_and_act(results: &[SearchResult]) -> Result<(), Box<dyn std::error::Error>> {
    if results.is_empty() {
        println!("No results.");
        return Ok(());
    }
    let _guard = TerminalGuard::enter()?;
    let mut selected = 0usize;
    let mut offset = 0usize;
    let mut action_menu = false;
    let mut action_selected = 0usize;
    let actions = [ActionKind::Open, ActionKind::Reveal, ActionKind::CopyPath, ActionKind::CopyName];

    loop {
        draw(results, selected, offset, action_menu, action_selected)?;
        match event::read()? {
            Event::Key(key) => match key.code {
                KeyCode::Esc => return Ok(()),
                KeyCode::Up => {
                    if action_menu {
                        action_selected = action_selected.saturating_sub(1);
                    } else if selected > 0 {
                        selected -= 1;
                        if selected < offset { offset = selected; }
                    }
                }
                KeyCode::Down => {
                    if action_menu {
                        if action_selected + 1 < actions.len() { action_selected += 1; }
                    } else if selected + 1 < results.len() {
                        selected += 1;
                        let height = visible_rows();
                        if selected >= offset + height { offset = selected + 1 - height; }
                    }
                }
                KeyCode::Right => { action_menu = true; action_selected = 0; }
                KeyCode::Left => { action_menu = false; }
                KeyCode::Enter => {
                    let path = &results[selected].path;
                    let action = if action_menu { actions[action_selected] } else { ActionKind::Open };
                    drop(_guard);
                    run_action(action, path, None)?;
                    return Ok(());
                }
                _ => {}
            },
            _ => {}
        }
    }
}

fn visible_rows() -> usize {
    let (_, rows) = terminal::size().unwrap_or((100, 30));
    rows.saturating_sub(6).max(5) as usize
}

fn draw(results: &[SearchResult], selected: usize, offset: usize, menu: bool, menu_sel: usize) -> std::io::Result<()> {
    let mut out = stdout();
    let (cols, rows) = terminal::size().unwrap_or((100, 30));
    queue!(out, Clear(ClearType::All), MoveTo(0, 0))?;
    queue!(out, SetAttribute(Attribute::Bold), Print(format!("eskit  {} result(s)", results.len())), SetAttribute(Attribute::Reset), Print("\n"))?;
    queue!(out, Print("↑/↓ select   → actions   Enter run   Esc quit\n"))?;
    queue!(out, Print("─".repeat(cols as usize)), Print("\n"))?;
    let max_rows = visible_rows();
    for (line, item) in results.iter().enumerate().skip(offset).take(max_rows) {
        let marker = if line == selected { "›" } else { " " };
        if line == selected { queue!(out, SetAttribute(Attribute::Reverse))?; }
        let name = basename(&item.path);
        let meta = format!("{}  {}  {}", item.kind, format_size(item.size), format_time(item.modified_unix));
        let mut row = format!("{} {:>3}. {:<42} {:<28} {}", marker, line + 1, truncate(&name, 42), truncate(&meta, 28), item.path);
        if row.chars().count() > cols as usize { row = truncate(&row, cols as usize); }
        queue!(out, Print(row), SetAttribute(Attribute::Reset), Print("\n"))?;
    }
    if menu {
        let menu_x = cols.saturating_sub(28);
        let menu_y = 4;
        let labels = ["Open", "Reveal in Explorer", "Copy path", "Copy name"];
        for (i, label) in labels.iter().enumerate() {
            queue!(out, MoveTo(menu_x, menu_y + i as u16))?;
            if i == menu_sel { queue!(out, SetAttribute(Attribute::Reverse))?; }
            queue!(out, Print(format!(" {:<24} ", label)), SetAttribute(Attribute::Reset))?;
        }
    }
    queue!(out, MoveTo(0, rows.saturating_sub(1)))?;
    queue!(out, Print(format!("Selected: {}", results.get(selected).map(|r| r.path.as_str()).unwrap_or(""))))?;
    out.flush()?;
    Ok(())
}

fn truncate(s: &str, max: usize) -> String {
    if s.chars().count() <= max { return s.to_string(); }
    if max <= 1 { return "…".to_string(); }
    let mut out: String = s.chars().take(max - 1).collect();
    out.push('…');
    out
}
