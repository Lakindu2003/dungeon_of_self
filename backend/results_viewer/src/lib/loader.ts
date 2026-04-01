import JSZip from 'jszip';
import type { RunData } from '../types/run';

export async function loadRunsFromFiles(files: FileList | File[]): Promise<RunData[]> {
  const runsMap: Record<string, Partial<RunData>> = {};

  const fileArray = Array.from(files);

  for (const file of fileArray) {
    if (file.name.endsWith('.zip')) {
      const zip = new JSZip();
      const loadedZip = await zip.loadAsync(file);

      // Collect all parseable JSON files
      const promises: Promise<void>[] = [];

      loadedZip.forEach((relativePath, zipEntry) => {
        if (zipEntry.dir) return;
        if (!relativePath.endsWith('.json')) return;

        promises.push((async () => {
          const content = await zipEntry.async('string');
          try {
            const data = JSON.parse(content);
            const pathParts = relativePath.split('/');
            const filename = pathParts.pop();
            // Let's assume the run folder name is the immediate parent directory name
            const folderPrefix = pathParts.length > 0 ? pathParts.join('/') : 'default_run';

            if (!runsMap[folderPrefix]) {
              runsMap[folderPrefix] = {};
            }

            const key = filename?.replace('.json', '');
            if (key) {
              (runsMap[folderPrefix] as any)[key] = data;
            }
          } catch (e) {
            console.error(`Failed to parse ${relativePath}`, e);
          }
        })());
      });

      await Promise.all(promises);
    } else if (file.name.endsWith('.json')) {
      // Direct drag and drop or selection
      // Use webkitRelativePath if available to determine the folder, otherwise fallback to "default_run"
      const pathParts = (file.webkitRelativePath || file.name).split('/');
      const filename = pathParts.pop();
      const folderPrefix = pathParts.length > 0 ? pathParts.join('/') : 'default_run';

      try {
        const text = await file.text();
        const data = JSON.parse(text);

        if (!runsMap[folderPrefix]) {
          runsMap[folderPrefix] = {};
        }

        const key = filename?.replace('.json', '');
        if (key) {
          (runsMap[folderPrefix] as any)[key] = data;
        }
      } catch (e) {
        console.error(`Failed to parse ${file.name}`, e);
      }
    }
  }

  // Convert map to array and ensure null fallbacks
  const results: RunData[] = [];
  for (const prefix of Object.keys(runsMap)) {
    const raw = runsMap[prefix];
    results.push({
      full_run: raw.full_run ?? null,
      skill_unlocks: raw.skill_unlocks ?? null,
      skills_summary: raw.skills_summary ?? null,
      incorrect_answers: raw.incorrect_answers ?? null,
      category_accuracy: raw.category_accuracy ?? null,
      ability_reroll: raw.ability_reroll ?? null,
      ability_flee: raw.ability_flee ?? null,
      ability_double_down: raw.ability_double_down ?? null,
    });
  }

  return results;
}