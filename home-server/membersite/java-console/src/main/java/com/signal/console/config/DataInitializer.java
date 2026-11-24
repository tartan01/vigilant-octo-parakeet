package com.signal.console.config;

import com.signal.console.model.Product;
import com.signal.console.repository.ShopRepository;
import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Component;

import java.util.List;

/** Seed the same six digital goods as membersite/store.py on an empty catalogue. */
@Component
public class DataInitializer implements CommandLineRunner {

    private final ShopRepository repo;

    public DataInitializer(ShopRepository repo) { this.repo = repo; }

    private static final String BRIEF = """
            # 金融科技信息简报 · 第 01 期

            一句话：把噪声折叠起来，只留下能改变判断的那几条。

            ## 信息源分享
            - 一手源优先：监管公告、交易所披露、发行人文件。二手解读只作导航。
            - 为每个源标注「更新频率 / 口径 / 滞后」，口径比数字本身更重要。
            - 建一份可回溯的清单：来源、抓取时间、校验人。三条，足矣。

            ## AI 信息分享
            - 用模型做「抽取与对齐」，不让它做「结论」。结论留给人。
            - 每条输出都带原文出处；无出处，即丢弃。
            - 提示词与版本入库，结果才可复现、可审计。

            ## 一句话
            信息差不在更多，而在更快被验证。
            """;

    @Override
    public void run(String... args) {
        if (repo.countProducts() > 0) return;
        List<Product> seeds = List.of(
                new Product("d1", "金融科技信息简报 · 第 01 期", "信息源分享 / AI 信息分享 · 极简版",
                        "一页纸的金融科技简报。只讲两件事：哪些信息源值得跟，以及 AI 该在哪一步介入。",
                        29.0, "研究简报", "", "编辑精选", -1, 0, null, "PDF · Markdown",
                        List.of("doc", "email", "link", "code", "online"), "约 1,200 字 / 2 页",
                        "SIGNAL 编辑部", "一句话：把噪声折叠起来，只留下能改变判断的那几条。",
                        BRIEF, "", "https://example.com/brief-01", "SIG-01", List.of(), ""),
                new Product("d2", "全球信息源清单 2026", "120+ 一手源 · 带口径与更新频率",
                        "按监管、市场、发行人、宏观四类整理的源清单，每条标注更新频率、口径与滞后。",
                        59.0, "信息源", "", "热卖", -1, 0, null, "CSV · Notion",
                        List.of("doc", "email", "link", "online"), "120 条 / 6 列",
                        "SIGNAL Research", "一手源优先：监管公告、交易所披露、发行人文件。",
                        "（完整清单共 120 条，购买后在线查阅或下载 CSV。）",
                        "", "https://example.com/sources-2026", "SRC-26", List.of(), ""),
                new Product("d3", "AI 信息处理工作流", "抽取 / 对齐 / 溯源 · 提示词库",
                        "一套可复用的提示词与流程说明：让模型做抽取与对齐，把结论留给人。",
                        79.0, "AI 资料", "", "", -1, 0, null, "Markdown · ZIP",
                        List.of("doc", "email", "code", "online"), "24 个提示词 / 5 个流程",
                        "SIGNAL Lab", "用模型做「抽取与对齐」，不让它做「结论」。",
                        "（24 个提示词与 5 段工作流，购买后在线查阅或下载 ZIP。）",
                        "", "", "", List.of(), ""),
                new Product("d4", "商业文档模板包", "合同 / 报告 / 会议纪要 · 18 份",
                        "干净、克制、可直接改的文档模板。统一字体、层级与留白。",
                        39.0, "文档模板", "", "", -1, 0, null, "DOCX · PDF · ZIP",
                        List.of("doc", "email", "link"), "18 份 / 约 6 MB",
                        "SIGNAL Studio", "统一字体、层级与留白，省下反复调格式的时间。",
                        "", "", "https://example.com/templates", "TPL-18", List.of(), ""),
                new Product("d5", "结构化数据集 · 试用装", "清洗好的样例数据 · 含字段字典",
                        "已清洗、带字段字典的样例数据集，用于验证流程与建模。",
                        19.0, "数据集", "", "新品", -1, 0, null, "CSV · JSON",
                        List.of("doc", "email", "link", "code"), "5,000 行 / 14 字段",
                        "SIGNAL Data", "已清洗、带字段字典的样例数据集。",
                        "", "", "https://example.com/dataset", "DATA-5K", List.of(), ""),
                new Product("d6", "年度订阅 · 全部简报", "每月两期 · 授权码即时开通",
                        "一次订阅，全年简报与信息源更新即时可用。以授权码开通。",
                        299.0, "订阅", "", "", -1, 0, null, "在线授权",
                        List.of("code", "online", "email"), "12 个月 / 24 期",
                        "SIGNAL 编辑部", "一次订阅，全年简报与信息源更新即时可用。",
                        "（订阅内容购买后在线查阅。）", "", "", "",
                        List.of("SIG-2026-A1", "SIG-2026-A2", "SIG-2026-A3"), "")
        );
        seeds.forEach(repo::saveProduct);
        System.out.println("[CONSOLE] Seeded " + seeds.size() + " digital products.");
    }
}
