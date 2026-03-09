"""
测试文件生成器 —— 生成覆盖所有检测类别的模拟测试文件
运行方式: python generate_test_files.py
"""
import os

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_files")


def ensure_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def write_txt(filename, content):
    filepath = os.path.join(OUTPUT_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  ✅ 已生成: {filename}")


def generate_classified_files():
    """生成涉密测试文件"""
    # 1. 含密级标识
    write_txt("01_绝密标识文件.txt", """
中华人民共和国某某部文件

                    绝密★

关于2024年度XX战略部署的报告

一、总体部署
根据中央指示精神，现将2024年度战略部署通知如下：
本文件包含绝密级战略部署信息，保密期限30年。
解密时间2054年。

二、具体方案
（此处省略具体内容）

                    某某部密发[2024]001号
""".strip())

    write_txt("02_机密标识文件.txt", """
机密★

关于XX地区军事部署调整方案

一、当前态势
根据最新情报分析，XX方向需要进行兵力调整。

二、调整方案
第XX集团军调动至XX地区，完成战备部署。
具体装备列装计划见附件。

保密期限：20年
""".strip())

    # 2. 含涉密关键词
    write_txt("03_涉密关键词文件.txt", """
XX研究所内部技术报告

一、核武器参数优化研究
本报告总结了2024年度核武器参数优化的阶段性成果。
洲际导弹射程参数已完成第三轮验证。
导弹制导算法v3.2已通过内部测试。

二、卫星加密算法升级
量子密钥分发参数已调整完毕，预计Q2完成部署。

三、情报来源分析
根据绝密情报，XX方向的线人信息需要重新评估。
间谍网络A-7的运行状态正常。
""".strip())


def generate_sensitive_files():
    """生成敏感信息测试文件"""
    # 3. PII信息
    write_txt("04_个人隐私信息文件.txt", """
员工信息登记表

姓名：张三
身份证号：110101199001011234
手机号码：138-0000-1234
电子邮箱：zhangsan@company.com
家庭住址：北京市朝阳区建国路88号院3号楼2单元1501室
护照号码：E12345678

紧急联系人信息：
姓名：李四
手机号码：139 0000 5678
身份证号：320102198505052345

银行卡信息：
工商银行：6222021234567890123
建设银行：6217001234567890
""".strip())

    # 4. 商业敏感
    write_txt("05_商业敏感信息文件.txt", """
仅限内部 —— 2024年Q3财务数据（未公开）

一、营收情况
未公开的Q3营收为52.3亿元，同比增长18.5%。
内部预算显示Q4预估营收将达到58亿元。
EBITDA利润率为23.4%（内部数据，不得外传）。

二、核心算法升级
自研推荐算法v4.0已完成内部测试，该核心算法为公司核心竞争优势。
专利技术"智能匹配引擎"已提交PCT申请。

三、客户名单更新
客户名单（仅限内部使用）：
- A集团：合同金额1.2亿，联系人王总 13900001111
- B科技：合同金额8000万，联系人赵总 13800002222

四、薪酬调整方案
2024年Q4绩效奖金方案（内部保密）：
- 张三：绩效评分A+，年薪80万，绩效奖金24万
- 李四：绩效评分B+，年薪55万，绩效奖金11万

本文件为商业秘密，未经授权禁止转载。
""".strip())


def generate_restricted_files():
    """生成受限使用内容测试文件"""
    write_txt("06_受限内容文件.txt", """
XX公司内部审计报告（仅限内部使用）

审计报告编号：IA-2024-0056
审计范围：2024年Q1-Q3财务及业务流程

一、审计发现
1. 采购流程存在合规风险（详见整改方案）。
2. 内审发现三项重大问题需立即整改。

二、会议纪要
本次党委会议决议（不得外传）：
- 同意XX项目立项
- 批准2025年预算方案

三、考试材料
2024年度岗位能力测试试卷
标准答案及评分标准见附件（考试用，严禁外泄）

四、版权声明
本文件版权所有 © 2024 XX公司
All Rights Reserved
未经书面授权禁止转载、复制或用于AI训练。
禁止用于AI训练或自动化处理。
""".strip())


def generate_risky_files():
    """生成风险内容测试文件"""
    write_txt("07_风险内容文件.txt", """
系统部署配置文档

一、数据库连接信息
MySQL主库：mysql://admin:P@ssw0rd123@10.20.30.40:3306/production_db
Redis缓存：redis://10.20.30.41:6379
MongoDB：mongodb://dbuser:Secret123@172.16.1.100:27017/app_data

二、API密钥配置
OpenAI API Key: sk-abcdefghijklmnopqrstuvwxyz1234567890ABCDEF
GitHub Token: ghp_1234567890abcdefghijklmnopqrstuvwxyz
AWS Access Key: AKIAIOSFODNN7EXAMPLE01
api_key = "a1b2c3d4e5f6g7h8i9j0k1l2m3n4"

三、服务器配置
生产环境Web服务器：10.20.30.50:8080
应用部署路径：/opt/deploy/app/production/v2.3.1
prod-server-01 配置已更新
staging-db-02 需要重启

四、登录凭证
后台管理密码：admin_P@ss2024!
SSH密钥：
-----BEGIN RSA PRIVATE KEY-----
MIIEpQIBAAKCAQEA0Z3VS5JJcds3xfn/ygWyF8PbnGy...
-----END RSA PRIVATE KEY-----

password = "Super$ecret!2024"
""".strip())


def generate_clean_file():
    """生成无问题的安全文件"""
    write_txt("08_安全文件.txt", """
2024年公司年度总结

一、业务回顾
2024年是公司发展的关键一年。我们在多个领域取得了重要突破，
团队规模持续扩大，产品能力不断提升。

二、技术创新
我们持续投入研发，在人工智能、云计算等前沿技术领域取得了
显著进展。多项技术获得业界认可。

三、社会责任
公司积极参与公益事业，累计向教育基金会捐赠物资若干，
组织员工志愿者活动多次。

四、未来展望
展望2025年，我们将继续秉承创新精神，为客户提供更优质的
产品和服务，努力实现更高的发展目标。

感谢全体员工的辛勤付出！
""".strip())


def generate_mixed_file():
    """生成混合多种问题的复杂文件"""
    write_txt("09_混合问题文件.txt", """
XX项目技术方案（内部资料，不得外传）

一、项目背景
本项目由国防科研院牵头，涉密科研项目编号：GF-2024-0088。
项目联系人：张工，手机号：13712345678，邮箱：zhangwork@defense.org

二、技术架构
数据库连接配置：
  postgresql://pgadmin:Str0ngPass!@10.10.20.100:5432/classified_data
应用部署路径：/opt/deploy/defense-project/v1.0/
API认证：api_key = "defense_api_key_2024_abcdefg123456"

三、核心参数
涉及导弹制导算法的关键参数已加密存储。
核心芯片设计源码存放于绝密服务器。

四、团队成员信息
成员1：王五，身份证号：420102199203033456，负责算法开发
成员2：赵六，身份证号：310101198807071234，负责系统集成

五、预算信息（未公开）
未公开的项目预算为3.8亿元，其中核心算法研发占比45%。
Q1已投入资金1.2亿元（内部数据）。

版权所有 © 2024 国防科研院
未经授权禁止转载或用于AI训练。
""".strip())


if __name__ == "__main__":
    print("=" * 50)
    print("  测试文件生成器")
    print("=" * 50)
    print()

    ensure_dir()

    print("📁 生成涉密测试文件...")
    generate_classified_files()

    print("\n📁 生成敏感信息测试文件...")
    generate_sensitive_files()

    print("\n📁 生成受限内容测试文件...")
    generate_restricted_files()

    print("\n📁 生成风险内容测试文件...")
    generate_risky_files()

    print("\n📁 生成安全文件...")
    generate_clean_file()

    print("\n📁 生成混合问题文件...")
    generate_mixed_file()

    print(f"\n✅ 所有测试文件已生成至: {OUTPUT_DIR}")
    print(f"   共 9 个测试文件，覆盖全部检测类别")
    print()
    print("使用说明:")
    print("  1. 启动系统: python app.py")
    print("  2. 打开浏览器访问 http://localhost:5000")
    print("  3. 上传 test_files 目录下的文件进行测试")
