//! Private terminal lifecycle and keyboard protocol for the field checklist.

use std::io;
use std::mem::MaybeUninit;
use std::sync::atomic::{AtomicI32, Ordering};

static INTERRUPTED: AtomicI32 = AtomicI32::new(0);

pub enum Key {
    Up,
    Down,
    Toggle,
    Save,
    Cancel,
    Ignore,
}

pub struct RawTerminal {
    original: libc::termios,
    handlers: Vec<(i32, libc::sigaction)>,
}

/// Record interruption without performing I/O from a signal handler.
/// Parameters: signal - delivered process signal number.
/// Returns: None.
extern "C" fn interrupt(signal: libc::c_int) {
    INTERRUPTED.store(signal, Ordering::Relaxed);
}

impl RawTerminal {
    /// Capture terminal settings, catch cancellation signals and enable raw input.
    /// Parameters: none; stdin is the already-verified interactive terminal.
    /// Returns: a restoring guard or a setup error without retaining raw mode.
    pub fn enter() -> Result<Self, String> {
        let mut original = MaybeUninit::<libc::termios>::uninit();
        // tcgetattr initializes the structure only on success.
        if unsafe { libc::tcgetattr(libc::STDIN_FILENO, original.as_mut_ptr()) } != 0 {
            return Err(io::Error::last_os_error().to_string());
        }
        let original = unsafe { original.assume_init() };
        let mut guard = Self {
            original,
            handlers: Vec::new(),
        };
        INTERRUPTED.store(0, Ordering::Relaxed);
        for signal in [libc::SIGINT, libc::SIGTERM, libc::SIGHUP] {
            // Zero initializes all fields, and sigemptyset initializes the mask.
            let mut handler: libc::sigaction = unsafe { std::mem::zeroed() };
            handler.sa_sigaction = interrupt as *const () as usize;
            unsafe { libc::sigemptyset(&mut handler.sa_mask) };
            let mut previous = MaybeUninit::<libc::sigaction>::uninit();
            if unsafe { libc::sigaction(signal, &handler, previous.as_mut_ptr()) } != 0 {
                return Err(io::Error::last_os_error().to_string());
            }
            guard
                .handlers
                .push((signal, unsafe { previous.assume_init() }));
        }
        let mut raw = original;
        unsafe { libc::cfmakeraw(&mut raw) };
        if unsafe { libc::tcsetattr(libc::STDIN_FILENO, libc::TCSANOW, &raw) } != 0 {
            return Err(io::Error::last_os_error().to_string());
        }
        Ok(guard)
    }
}

impl Drop for RawTerminal {
    /// Restore terminal mode and every previous signal disposition on all exits.
    /// Parameters: self - guard retaining the original terminal/process state.
    /// Returns: None.
    fn drop(&mut self) {
        unsafe { libc::tcsetattr(libc::STDIN_FILENO, libc::TCSANOW, &self.original) };
        for (signal, previous) in self.handlers.drain(..) {
            unsafe { libc::sigaction(signal, &previous, std::ptr::null_mut()) };
        }
    }
}

/// Read one byte with bounded polling and interruption/EOF cancellation.
/// Parameters: timeout_ms - optional escape-sequence timeout; absent waits for a key.
/// Returns: a byte, None on timeout/cancellation/EOF, or a terminal read error.
fn read_byte(timeout_ms: Option<i32>) -> Result<Option<u8>, String> {
    let mut descriptor = libc::pollfd {
        fd: libc::STDIN_FILENO,
        events: libc::POLLIN,
        revents: 0,
    };
    loop {
        if INTERRUPTED.load(Ordering::Relaxed) != 0 {
            return Ok(None);
        }
        let ready = unsafe { libc::poll(&mut descriptor, 1, timeout_ms.unwrap_or(100)) };
        if ready < 0 {
            let error = io::Error::last_os_error();
            if error.kind() == io::ErrorKind::Interrupted {
                continue;
            }
            return Err(error.to_string());
        }
        if ready == 0 {
            if timeout_ms.is_some() {
                return Ok(None);
            }
            continue;
        }
        let mut byte = [0];
        // Read the same descriptor that poll observes. Stdin's buffering can
        // prefetch escape-sequence bytes and leave poll waiting on an empty fd.
        let count = unsafe { libc::read(libc::STDIN_FILENO, byte.as_mut_ptr().cast(), 1) };
        if count == 0 {
            return Ok(None);
        }
        if count > 0 {
            return Ok(Some(byte[0]));
        }
        let error = io::Error::last_os_error();
        if error.kind() != io::ErrorKind::Interrupted {
            return Err(error.to_string());
        }
    }
}

/// Decode the checklist's key protocol without blocking on a bare Escape.
/// Parameters: none; raw bytes arrive on the guarded stdin terminal.
/// Returns: a navigation/toggle/save/cancel key or a terminal read error.
pub fn read_key() -> Result<Key, String> {
    match read_byte(None)? {
        Some(b'\x1b') => {
            let middle = read_byte(Some(60))?;
            let end = if middle.is_some() {
                read_byte(Some(60))?
            } else {
                None
            };
            Ok(match (middle, end) {
                (Some(b'['), Some(b'A')) => Key::Up,
                (Some(b'['), Some(b'B')) => Key::Down,
                (Some(b'['), Some(b'C' | b'D')) => Key::Ignore,
                _ => Key::Cancel,
            })
        }
        Some(b'\r' | b'\n') => Ok(Key::Save),
        Some(b' ') => Ok(Key::Toggle),
        Some(b'q' | b'\x03') | None => Ok(Key::Cancel),
        _ => Ok(Key::Ignore),
    }
}
