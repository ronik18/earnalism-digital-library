// Test-only upstream pure helper. No auth, HTTP, upload or deployment entrypoint.
use std::path::Path;
use std::sync::{Arc, Mutex};
use anyhow::Result;
use gzp::{ZBuilder, deflate::Gzip};
use ignore::WalkBuilder;
use synchronized_writer::SynchronizedWriter;
use tar::Builder;

pub fn create_deploy_tarball(
    project_path: &Path,
    archive_prefix_path: &Path,
    no_gitignore: bool,
    mut on_progress: impl FnMut(usize, usize),
) -> Result<Vec<u8>> {
    let bytes = Vec::<u8>::new();
    let arc = Arc::new(Mutex::new(bytes));
    let mut parz = ZBuilder::<Gzip, _>::new()
        .num_threads(num_cpus::get())
        .from_writer(SynchronizedWriter::new(arc.clone()));

    let ignore_paths = [".git", "node_modules"];
    let ignore_paths: Vec<&std::ffi::OsStr> =
        ignore_paths.iter().map(std::ffi::OsStr::new).collect();

    {
        let mut archive = Builder::new(&mut parz);
        let mut builder = WalkBuilder::new(project_path);
        builder.add_custom_ignore_filename(".railwayignore");
        if no_gitignore {
            builder.git_ignore(false);
        }

        let walker = builder.follow_links(true).hidden(false);
        let walked = walker.build().collect::<Vec<_>>();
        let total = walked.len();
        on_progress(0, total);

        for (i, entry) in walked.into_iter().enumerate() {
            let entry = entry?;
            let path = entry.path();
            if path
                .components()
                .any(|c| ignore_paths.contains(&c.as_os_str()))
            {
                continue;
            }
            let stripped =
                std::path::PathBuf::from(".").join(path.strip_prefix(archive_prefix_path)?);
            archive.append_path_with_name(path, stripped)?;
            on_progress(i + 1, total);
        }
    }
    parz.finish()?;

    let body = Arc::try_unwrap(arc)
        .map_err(|_| {
            anyhow::anyhow!("internal error: tarball buffer still has references after compression")
        })?
        .into_inner()
        .map_err(|e| anyhow::anyhow!("internal error: failed to unwrap tarball buffer: {e}"))?;
    Ok(body)
}

fn main() -> Result<()> {
    let args: Vec<String> = std::env::args().collect();
    anyhow::ensure!(args.len() == 4, "expected PROJECT_PATH ARCHIVE_PREFIX OUTPUT");
    let body = create_deploy_tarball(Path::new(&args[1]), Path::new(&args[2]), false, |_, _| {})?;
    use std::io::Write;
    let mut out = std::fs::OpenOptions::new().write(true).create_new(true).open(&args[3])?;
    out.write_all(&body)?;
    Ok(())
}
