using System;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.IO.Compression;
using System.Reflection;
using System.Text;
using System.Threading.Tasks;
using System.Windows.Forms;

[assembly: AssemblyTitle("克里姆林宫危机：冷战 简体中文汉化补丁")]
[assembly: AssemblyProduct("克里姆林宫危机：冷战 简体中文汉化补丁")]
[assembly: AssemblyVersion("1.2.1.0")]

internal sealed class Payload : IDisposable
{
    private string folder;

    public void Prepare()
    {
        if (folder != null) return;
        var staging = Path.Combine(Path.GetTempPath(), "SteamZhCN-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(staging);
        try
        {
            Extract(staging);
            folder = staging;
        }
        catch
        {
            RemoveTemp(staging);
            throw;
        }
    }

    private static void Extract(string folder)
    {
        using (Stream source = Assembly.GetExecutingAssembly().GetManifestResourceStream("patch.zip"))
        using (ZipArchive archive = new ZipArchive(source, ZipArchiveMode.Read))
        {
            string prefix = Path.GetFullPath(folder) + Path.DirectorySeparatorChar;
            foreach (ZipArchiveEntry entry in archive.Entries)
            {
                string path = Path.GetFullPath(Path.Combine(folder, entry.FullName));
                if (!path.StartsWith(prefix, StringComparison.OrdinalIgnoreCase))
                    throw new InvalidDataException("安装文件路径无效，请重新下载安装程序。");
                if (entry.Name.Length == 0) continue;
                Directory.CreateDirectory(Path.GetDirectoryName(path));
                using (Stream input = entry.Open())
                using (FileStream output = new FileStream(path, FileMode.CreateNew, FileAccess.Write))
                    input.CopyTo(output);
            }
        }
    }

    // The only variable argument is a validated Windows directory. Escape terminal slashes
    // as required by the Windows command-line parser when the directory is a drive root.
    private static string QuotePath(string path)
    {
        if (path.Contains("\"")) throw new ArgumentException("游戏路径无效。");
        string plain = path.TrimEnd('\\');
        return "\"" + plain + new string('\\', (path.Length - plain.Length) * 2) + "\"";
    }

    public string Run(string action, string game, Action<string> report)
    {
        var info = new ProcessStartInfo(Path.Combine(folder, "runtime", "python.exe"));
        info.WorkingDirectory = folder;
        info.Arguments = "-B -u -X utf8 manage.py " + action;
        if (game != null) info.Arguments += " --game-dir " + QuotePath(game);
        info.UseShellExecute = false;
        info.CreateNoWindow = true;
        info.RedirectStandardInput = info.RedirectStandardError = info.RedirectStandardOutput = true;
        info.StandardOutputEncoding = info.StandardErrorEncoding = Encoding.UTF8;
        using (var proc = new Process { StartInfo = info })
        {
            proc.Start();
            proc.StandardInput.Close();
            Task<string> errors = proc.StandardError.ReadToEndAsync();
            string line, last = "";
            while ((line = proc.StandardOutput.ReadLine()) != null)
            {
                if (line.Trim().Length == 0) continue;
                last = line;
                if (report != null) report(line);
            }
            proc.WaitForExit();
            string error = errors.GetAwaiter().GetResult().Trim();
            if (proc.ExitCode != 0)
                throw new InvalidOperationException(error.Length > 0 ? error :
                    (last.Length > 0 ? last : "操作没有完成。请关闭游戏后重试。"));
            return last;
        }
    }

    private static void RemoveTemp(string folder)
    {
        if (folder == null) return;
        try { Directory.Delete(folder, true); }
        catch (IOException) { }
        catch (UnauthorizedAccessException) { }
    }

    public void Dispose() { RemoveTemp(folder); }
}

internal sealed class Installer : Form
{
    private readonly Payload payload;
    private readonly TextBox path = new TextBox();
    private readonly Label version = new Label();
    private readonly Label status = new Label();
    private readonly Button install = new Button();
    private readonly Button browse = new Button();
    private readonly LinkLabel restore = new LinkLabel();
    private readonly LinkLabel verify = new LinkLabel();
    private readonly ProgressBar progress = new ProgressBar();
    private bool busy;
    private string game;

    public Installer(Payload payload)
    {
        this.payload = payload;
        Text = "克里姆林宫危机：冷战 · 汉化补丁";
        Font = new Font("Microsoft YaHei UI", 10F);
        AutoScaleMode = AutoScaleMode.Font;
        BackColor = Color.White;
        ClientSize = new Size(610, 290);
        MinimumSize = new Size(560, 320);
        MaximizeBox = false;
        StartPosition = FormStartPosition.CenterScreen;

        var panel = new TableLayoutPanel {
            Dock = DockStyle.Fill, Padding = new Padding(24,18,24,18),
            ColumnCount = 2, RowCount = 6
        };
        panel.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        panel.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
        foreach (int height in new int[] {42,32,42,48,16})
            panel.RowStyles.Add(new RowStyle(SizeType.Absolute, height));
        panel.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
        var title = new Label {
            Text = "克里姆林宫危机：冷战", AutoSize = true, Anchor = AnchorStyles.Left,
            Font = new Font(Font.FontFamily, 16, FontStyle.Bold)
        };
        version.Text = "汉化 v1.2.1　·　适配 Steam 构建 26243566";
        version.AutoSize = true;
        version.Anchor = AnchorStyles.Left;
        panel.Controls.Add(title,0,0); panel.SetColumnSpan(title,2);
        panel.Controls.Add(version,0,1); panel.SetColumnSpan(version,2);

        path.ReadOnly = true;
        path.BackColor = Color.White;
        path.AccessibleName = "Steam 游戏目录";
        path.Anchor = AnchorStyles.Left | AnchorStyles.Right;
        path.Text = "正在查找 Steam 游戏目录…";
        browse.Text = "选择目录…";
        browse.AutoSize = true;
        browse.Anchor = AnchorStyles.Right;
        browse.Click += async delegate { await ChooseFolder(); };
        panel.Controls.Add(path,0,2); panel.Controls.Add(browse,1,2);
        status.Dock = DockStyle.Fill;
        status.TextAlign = ContentAlignment.MiddleLeft;
        status.AutoEllipsis = true;
        panel.Controls.Add(status,0,3); panel.SetColumnSpan(status,2);
        progress.Dock = DockStyle.Fill;
        panel.Controls.Add(progress,0,4); panel.SetColumnSpan(progress,2);
        restore.Text = "还原原版";
        restore.AutoSize = true;
        restore.Anchor = AnchorStyles.Left;
        verify.Text = "核验汉化";
        verify.AutoSize = true;
        verify.Click += async delegate { await Apply("verify"); };
        restore.Click += async delegate {
            if (MessageBox.Show(this,"还原本补丁修改的文件和设置？","还原原版",MessageBoxButtons.YesNo,
                MessageBoxIcon.Question,MessageBoxDefaultButton.Button2) == DialogResult.Yes) await Apply("restore");
        };
        install.Text = "安装汉化";
        install.AutoSize = true;
        install.Padding = new Padding(12,3,12,3);
        install.Anchor = AnchorStyles.Right;
        install.Click += async delegate { await Apply("install"); };
        var tools = new FlowLayoutPanel { AutoSize = true, WrapContents = false, Anchor = AnchorStyles.Left };
        tools.Controls.Add(verify);
        restore.Margin = new Padding(16, 0, 0, 0);
        tools.Controls.Add(restore);
        panel.Controls.Add(tools,0,5); panel.Controls.Add(install,1,5);
        Controls.Add(panel);
        AcceptButton = install;
        Shown += async delegate { await Detect(null); };
        FormClosing += delegate(object sender, FormClosingEventArgs args) { args.Cancel = busy; };
    }

    private void SetBusy(bool active)
    {
        busy = active;
        install.Enabled = restore.Enabled = verify.Enabled = !active && game != null;
        browse.Enabled = !active;
        progress.Style = active ? ProgressBarStyle.Marquee : ProgressBarStyle.Blocks;
        progress.Value = 0;
    }

    private async Task Detect(string selected)
    {
        SetBusy(true);
        try
        {
            var found = await Task.Run(delegate {
                payload.Prepare();
                string located = payload.Run("locate",selected,null);
                return Tuple.Create(located, payload.Run("build",located,null));
            });
            game = found.Item1;
            path.Text = game;
            version.Text = "汉化 v1.2.1　·　适配 26243566　·　本机 " +
                           (found.Item2 == "unknown" ? "未读到构建号" : found.Item2);
            status.Text = found.Item2 != "unknown" && found.Item2 != "26243566"
                ? "游戏构建与适配版本不同。安装前会核对文件，请留意兼容性提示。"
                : "已找到游戏。可安装汉化，或核验现有安装。";
        }
        catch (Exception ex)
        {
            if (selected != null) MessageBox.Show(this,ex.Message,"无法使用此目录",MessageBoxButtons.OK,MessageBoxIcon.Information);
            if (game == null) path.Text = "请选择游戏主目录";
            status.Text = ex.Message;
        }
        finally { SetBusy(false); }
    }

    private async Task ChooseFolder()
    {
        using (var dialog = new FolderBrowserDialog { Description = "选择包含游戏主程序的目录", ShowNewFolderButton = false })
        {
            if (game != null) dialog.SelectedPath = game;
            if (dialog.ShowDialog(this) == DialogResult.OK) await Detect(dialog.SelectedPath);
        }
    }

    private async Task Apply(string action)
    {
        SetBusy(true);
        status.Text = action == "install" ? "正在安装，请稍候…" : action == "verify" ? "正在核验汉化…" : "正在还原…";
        try
        {
            await Task.Run(delegate {
                payload.Run(action,game,delegate(string line) {
                    BeginInvoke((Action)delegate { status.Text = line; });
                });
                if (action == "install") payload.Run("verify",game,null);
            });
            string message = action == "install" ? "汉化已安装并核验。现在可从 Steam 启动游戏。" : action == "verify" ? "核验通过，汉化文件完整。" : "已还原。";
            status.Text = message;
            MessageBox.Show(this,message,Text,MessageBoxButtons.OK,MessageBoxIcon.Information);
        }
        catch (Exception ex)
        {
            status.Text = "操作未完成，可以重试。";
            MessageBox.Show(this,ex.Message,Text,MessageBoxButtons.OK,MessageBoxIcon.Warning);
        }
        finally { SetBusy(false); }
    }
}

internal static class Program
{
    [STAThread]
    private static int Main(string[] args)
    {
        using (var payload = new Payload())
        {
            if (args.Length > 0)
            {
                try
                {
                    Console.SetOut(new StreamWriter(Console.OpenStandardOutput(), new UTF8Encoding(false)) { AutoFlush = true });
                    Console.SetError(new StreamWriter(Console.OpenStandardError(), new UTF8Encoding(false)) { AutoFlush = true });
                    string action = args[0].TrimStart('-');
                    if (action != "locate" && action != "build" && action != "install" && action != "verify" && action != "restore")
                        throw new ArgumentException("可用操作：--locate、--build、--install、--verify、--restore [游戏目录]");
                    if (args.Length > 2) throw new ArgumentException("最多可指定一个游戏目录。");
                    payload.Prepare();
                    string selected = args.Length == 2 ? args[1] : null;
                    payload.Run(action,selected,Console.WriteLine);
                    if (action == "install") payload.Run("verify",selected,Console.WriteLine);
                    return 0;
                }
                catch (Exception ex) { Console.Error.WriteLine(ex.Message); return 1; }
            }
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            Application.Run(new Installer(payload));
            return 0;
        }
    }
}
