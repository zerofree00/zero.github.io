---
layout: default
title: Zero 的博客
---

<section class="home-hero">
  <div class="hero-copy-block">
    <p class="eyebrow">PROGRAMMER NOTES</p>
    <h1>Zero 的开发手记</h1>
    <p class="hero-copy">
      记录写代码、搭博客、排查问题和持续学习时踩过的坑。这里像一个轻量工作台，把思路、命令、错误和修复都留下来。
    </p>
    <div class="hero-actions">
      <a class="primary-link" href="https://zerofree00.github.io/zero.github.io/">访问博客首页</a>
      <a class="secondary-link" href="https://github.com/zerofree00/zero.github.io">查看 GitHub 仓库</a>
    </div>
    <div class="hero-stats" aria-label="博客状态">
      <span><strong>9</strong> articles</span>
      <span><strong>4</strong> dev notes</span>
      <span><strong>gh-pages</strong> branch</span>
    </div>
  </div>

  <div class="terminal-panel" aria-label="终端预览">
    <div class="terminal-bar">
      <span></span>
      <span></span>
      <span></span>
      <strong>zero.github.io</strong>
    </div>
    <pre><code>$ git status --short --branch
## gh-pages...origin/gh-pages

$ bundle exec jekyll build
done in 0.42 seconds

$ open /2026/04/30/debug-404.html
status: 200 OK</code></pre>
  </div>
</section>

<section class="topic-strip" aria-label="博客主题">
  <span>Git</span>
  <span>GitHub Pages</span>
  <span>Jekyll</span>
  <span>Debugging</span>
  <span>Learning</span>
</section>

## 程序员文章

<p class="section-intro">这些文章更偏真实工程现场：搭建、发布、链接、404、Git 工作流。</p>

<div class="post-grid">
  <article class="post-card featured">
    <p class="post-meta">工程实践 · GitHub Pages</p>
    <h3><a href="https://zerofree00.github.io/zero.github.io/2026/04/30/github-pages-blog-setup.html">一次 GitHub Pages 博客搭建记录</a></h3>
    <p>从克隆仓库、写第一篇文章，到处理 baseurl 和推送失败，把一次真实搭建过程整理成可复用的笔记。</p>
  </article>

  <article class="post-card">
    <p class="post-meta">Jekyll · 排错</p>
    <h3><a href="https://zerofree00.github.io/zero.github.io/2026/04/30/jekyll-future-posts.html">未来日期导致 Jekyll 文章不发布</a></h3>
    <p>新文章链接 404 的原因并不复杂：日期写到了未来。这个小坑很适合拿来理解静态站点的构建逻辑。</p>
  </article>

  <article class="post-card">
    <p class="post-meta">Git · 工作流</p>
    <h3><a href="https://zerofree00.github.io/zero.github.io/2026/04/30/small-commits.html">小步提交是一种安全感</a></h3>
    <p>提交不是仪式感，而是给自己留下可回退、可解释、可继续推进的工作现场。</p>
  </article>

  <article class=”post-card”>
    <p class=”post-meta”>Debugging · 方法</p>
    <h3><a href=”https://zerofree00.github.io/zero.github.io/2026/04/30/debug-404.html”>遇到 404 时，我会怎么排查</a></h3>
    <p>从 URL、构建产物、文件日期和配置路径开始，一步步把”打不开”变成一个具体问题。</p>
  </article>

  <article class=”post-card”>
    <p class=”post-meta”>工具 · Python</p>
    <h3><a href=”https://zerofree00.github.io/zero.github.io/2026/05/14/music-search-tool.html”>歌曲宝：一个本地音乐搜索下载小工具</a></h3>
    <p>支持三个数据源的本地音乐搜索下载工具，双击 bat 即可使用，也有在线搜索页面。</p>
  </article>
</div>

## 随笔

- [把复杂问题拆小一点](https://zerofree00.github.io/zero.github.io/2026/04/30/break-big-problems-down.html)
- [给生活留一点空白](https://zerofree00.github.io/zero.github.io/2026/04/30/leave-some-blank-space.html)
- [学习技术时，先让它跑起来](https://zerofree00.github.io/zero.github.io/2026/04/30/make-it-run-first.html)
- [在不确定里保持前进](https://zerofree00.github.io/zero.github.io/2026/04/30/keep-moving-in-uncertainty.html)

## 关于这里

这个博客会放一些程序员日常会遇到的东西：一次排查、一个小坑、一段学习记录，或者一个终于想明白的工程习惯。
