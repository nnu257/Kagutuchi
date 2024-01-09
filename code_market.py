codes_info = open("datas/code/20231008205049.tsv", "r").read().splitlines()[1:]
codes_info = [code_info.split("\t") for code_info in codes_info]

codes_prime = [code_info[2][:-1] for code_info in codes_info if code_info[11] == "プライム"]
codes_standard = [code_info[2][:-1] for code_info in codes_info if code_info[11] == "スタンダード"]
codes_grows = [code_info[2][:-1] for code_info in codes_info if code_info[11] == "グロース"]

codes_topix100 = [code_info[2][:-1] for code_info in codes_info if code_info[9] == "TOPIX Core30" or code_info[9] == "TOPIX Large70"]
codes_topix500 = [code_info[2][:-1] for code_info in codes_info if code_info[9] == "TOPIX Core30" or code_info[9] == "TOPIX Large70" or code_info[9] == "TOPIX Mid400"]


PREFIX = "datas/code_market/"
def writes(contents, filename):
    open(PREFIX + filename, "w").write(", ".join(contents))
    
writes(codes_prime, "prime.csv")
writes(codes_standard, "standard.csv")
writes(codes_grows, "grows.csv")
writes(codes_topix100, "topix100.csv")
writes(codes_topix500, "topix500.csv")