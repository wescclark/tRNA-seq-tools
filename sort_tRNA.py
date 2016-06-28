import os 
import sys
import fnmatch
import Oligotyping.lib.fastalib as u 
import argparse
import csv
import Levenshtein as lev

# commit to github change

class SorterStats:
    def __init__(self):
        self.total_seqs = 0
        self.total_rejected = 0
        self.total_passed = 0
        self.total_full_length = 0

        self.no_divergence = 0
        self.t_loop_divergence = 0
        self.div_at_0 = 0
        self.div_at_1 = 0
        self.div_at_2 = 0
        self.div_at_3 = 0
        self.div_at_8 = 0
        self.acceptor_divergence = 0
        self.div_at_neg_1 = 0
        self.div_at_neg_2 = 0
        self.div_at_neg_3 = 0

        self.t_loop_seq_rejected = 0
        self.acceptor_seq_rejected = 0
        self.both_rejected = 0
        self.short_rejected = 0

    def format_line(self, label, value, level, padding = 55):
        levels_dict = {1:"%s%s\t%s\n" % 
            (label, " " + " " * (padding - len(label)), value),
            2:"\t%s%s\t%s\n" % 
                (label, " " + " " * (padding - (4 + len(label))), value),
            3:"\t\t%s%s\t%s\n" % 
                (label, " " + " " * (padding - (12 + len(label))), value)}
        return levels_dict[level]

    def write_stats(self, out_file_path):
        with open(out_file_path, "w") as outfile:
            outfile.write(self.format_line("Total seqs", "%d" % 
                self.total_seqs,1))
            outfile.write(self.format_line("Total full-length", "%d" %
                self.total_full_length, 1))
            outfile.write(self.format_line("Total passed", "%d" % 
                self.total_passed, 1))

            outfile.write(self.format_line("No divergence", "%d" % 
                self.no_divergence, 2))
            outfile.write(self.format_line("T-loop divergence", "%d" % 
                self.t_loop_divergence, 2))
            outfile.write(self.format_line("Divergence at pos 0", "%d" % 
                self.div_at_0, 3))
            outfile.write(self.format_line("Divergence at pos 1", "%d" % 
                self.div_at_1, 3))
            outfile.write(self.format_line("Divergence at pos 2", "%d" % 
                self.div_at_2, 3))
            outfile.write(self.format_line("Divergence at pos 3", "%d" % 
                self.div_at_3, 3))
            outfile.write(self.format_line("Divergence at pos 8", "%d" %
                self.div_at_8, 3))
            outfile.write(self.format_line("Acceptor divergence", "%d" % 
                self.acceptor_divergence, 2))
            outfile.write(self.format_line("Divergence at pos -3", "%d" % 
                self.div_at_neg_3, 3))
            outfile.write(self.format_line("Divergence at pos -2", "%d" % 
                self.div_at_neg_2, 3))
            outfile.write(self.format_line("Divergence at pos -1", "%d" % 
                self.div_at_neg_1, 3))

            outfile.write(self.format_line("Total failed", "%d" % 
                self.total_rejected, 1))
            outfile.write(self.format_line("T-loop seq rejected", "%d" % 
                self.t_loop_seq_rejected, 2))
            outfile.write(self.format_line("Acceptor seq rejected", "%d" % 
                self.acceptor_seq_rejected, 2))
            outfile.write(self.format_line("Both rejected", "%d" % 
                self.both_rejected, 2))
            outfile.write(self.format_line("Short rejected", "%d" % 
                self.short_rejected, 2))
 
       
class SeqSpecs:
    def __init__(self):
        self.length = 0
        self.mis_count = 100
        self.t_loop_error = True
        self.acceptor_error = True
        self.seq = ""
        self.seq_sub = ""
        self.full_length = False
        self.t_loop_seq = ""
        self.acceptor_seq = ""
        self.five_trailer = ""
        self.no_trailer_length = 0
        self.trailer_length = 0

    def gen_id_string(self, id):
        mod_id_list = []
        mod_id_list.append(id)
        mod_id_list.append("mismatches:" + str(self.mis_count))
        mod_id_list.append("t_loop_error:" + str(self.t_loop_error))
        mod_id_list.append("acceptor_error:" + str(self.acceptor_error))
        mod_id_list.append("seq_sub:" + self.seq_sub)
        if self.full_length:
            mod_id_list.append("full length: Yes")
        else:
            mod_id_list.append("full length: Maybe")
        mod_id_list.append("t_loop:" + self.t_loop_seq)
        mod_id_list.append("acceptor:" + self.acceptor_seq)
        mod_id_list.append("5_trailer:" + self.five_trailer)
        return "|".join(mod_id_list)

    def write_specs(self, writer, id):
        writer.writerow([id, self.seq, self.five_trailer, self.t_loop_seq,
            self.acceptor_seq, str(self.full_length),
            str(self.length)])

class Sorter:
    def __init__(self, args):
        self.read_fasta = u.SequenceSource(args.readfile)
        self.passed_seqs_write_fasta = u.FastaOutput("sort_passed")
        self.rejected_seqs_write_fasta = u.FastaOutput("sort_failed")

       #self.passed_seqs_write_fasta = u.FastaOutput(args.passed_writefile)
       #self.rejected_seqs_write_fasta = u.FastaOutput(args.rejected_writefile)
   
        self.stats = SorterStats()


    def is_tRNA(self, seq):
        length = len(seq)
        sub_size = 24
        t_loop_error = True
        acceptor_error = True
        cur_seq_specs = SeqSpecs()
        for i in xrange(length - sub_size + 1):
            sub_str = seq[-(i + sub_size):(length - i)]
            t_loop_seq = sub_str[0:9]
            acceptor_seq = sub_str[-3:]
            t_loop_dist = (lev.distance("GTTC", sub_str[0:4]) 
                + lev.distance("C", sub_str[8]))
            acceptor_dist = lev.distance("CCA", sub_str[-3:])
            mis_count = t_loop_dist + acceptor_dist
            
            if t_loop_dist < 1:    
                t_loop_error = False
            else:
                t_loop_error = True
            if acceptor_dist < 1:
                acceptor_error = False
            else:
                acceptor_error = True
            if mis_count < cur_seq_specs.mis_count:
                cur_seq_specs.length = length
                cur_seq_specs.mis_count = mis_count
                cur_seq_specs.t_loop_error = t_loop_error
                cur_seq_specs.acceptor_error = acceptor_error
                cur_seq_specs.seq = seq
                cur_seq_specs.seq_sub = sub_str
                cur_seq_specs.t_loop_seq = t_loop_seq
                cur_seq_specs.acceptor_seq = acceptor_seq
            if mis_count < 2:   
                self.stats.total_passed += 1
                
                # checking divergence at specific positions
                if cur_seq_specs.t_loop_error:
                    self.stats.t_loop_divergence += 1
                    if sub_str[0] != "G":
                        self.stats.div_at_0 += 1
                    elif sub_str[1] != "T":
                        self.stats.div_at_1 += 1
                    elif sub_str[2] != "T":
                        self.stats.div_at_2 += 1
                    elif sub_str[3] != "C":
                        self.stats.div_at_3 += 1
                    elif sub_str[8] != "C":
                        self.stats.div_at_8 += 1
                elif cur_seq_specs.acceptor_error:
                    self.stats.acceptor_divergence += 1
                    if sub_str[-3] != "C":
                        self.stats.div_at_neg_3 += 1
                    elif sub_str[-2] != "C":
                        self.stats.div_at_neg_2 += 1
                    elif sub_str[-1] != "A":
                        self.stats.div_at_neg_1 += 1
                else:
                    self.stats.no_divergence += 1

                # full-length id
                if length > 70 and length < 100:
                    if seq[7] == "T" and seq[13] == "A":
                        self.stats.total_full_length += 1
                        cur_seq_specs.full_length = True
                
                # split 5_trailer
                cur_seq_specs.seq = seq[:(length - i)]
                cur_seq_specs.five_trailer = seq[(length - i):]
                cur_seq_specs.no_trailer_length = len(cur_seq_specs.seq)
                cur_seq_specs.trailer_length = len(cur_seq_specs.five_trailer)

                res_tup = (True, cur_seq_specs)
                return res_tup

        if cur_seq_specs.t_loop_error and cur_seq_specs.acceptor_error:
            if length < 24:
                self.stats.short_rejected += 1
            else:
                self.stats.both_rejected += 1
        elif cur_seq_specs.acceptor_error and not cur_seq_specs.t_loop_error:
            self.stats.acceptor_seq_rejected += 1
        elif cur_seq_specs.t_loop_error and not cur_seq_specs.acceptor_error:
            self.stats.t_loop_seq_rejected += 1
        self.stats.total_rejected += 1
        res_tup = (False, cur_seq_specs)
        return res_tup


    def run(self):
        print "sort started"
        temp_tabfile = open("tab_passed", "w+")
        spec_writer = csv.writer(temp_tabfile, delimiter="\t")
        spec_writer.writerow(["ID", "Seq", "5-trailer", "t-loop",
            "acceptor", "full-length", "Seq length"])
        max_no_trailer_length = 0
        max_trailer_length = 0

        while self.read_fasta.next():
            self.stats.total_seqs += 1
            is_tRNA_result = self.is_tRNA(self.read_fasta.seq.upper())
          
           #inserted exit statement to make sure I'm only looking at one
           #sequence  
           #exit(1)

            mod_id = is_tRNA_result[1].gen_id_string(
                self.read_fasta.id.split('|')[0]) 
            if is_tRNA_result[0]:
                self.passed_seqs_write_fasta.write_id(mod_id)
                self.passed_seqs_write_fasta.write_seq(is_tRNA_result[1].seq)
                is_tRNA_result[1].write_specs(spec_writer, 
                    self.read_fasta.id.split('|')[0])
                if is_tRNA_result[1].no_trailer_length > max_no_trailer_length:
                    max_no_trailer_length = is_tRNA_result[1].no_trailer_length
                if is_tRNA_result[1].trailer_length > max_trailer_length:
                    max_trailer_length = is_tRNA_result[1].trailer_length
            else:
                self.rejected_seqs_write_fasta.write_id(mod_id)
                self.rejected_seqs_write_fasta.write_seq(is_tRNA_result[1].seq)
        temp_tabfile.close()
        print max_no_trailer_length
        print max_trailer_length
        with open("sort_tab_passed", "w") as tabfile:
            tabfile_writer = csv.writer(tabfile, delimiter="\t")
            with open("tab_passed", "r") as temp_tabfile: 
                temp_tabfile_reader = csv.reader(temp_tabfile, delimiter="\t")
                for row in temp_tabfile_reader:
                    row[1] = ("{:>" + str(max_no_trailer_length) + "}").format(row[1])
                    row[2] = ("{:>" + str(max_trailer_length) +
                        "}").format(row[2])
                    tabfile_writer.writerow(row)
        
        self.write_sorted()
        self.stats.write_stats("sort_stats")
        print "sort finished"


    def write_sorted(self):
        sort_dict = {}
        with open("tab_passed", "r") as temp_tabfile:  
            temp_tabfile_reader = csv.reader(temp_tabfile, delimiter="\t")
            for row in temp_tabfile_reader:
                sort_dict[row[6]].append(row)
        
        with open("sort_tab_passed_sorted", "w") as tabfile:
            tabfile_writer = csv.writer(tabfile, delimiter="\t")
            for key, row in sorted(sort_dict):
                row[1] = ("{:>" + str(max_no_trailer_length) + "}").format(row[1])
                row[2] = ("{:>" + str(max_trailer_length) +
                    "}").format(row[2])
                tabfile_writer.writerow(row)
        

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Sort tRNAs")
    parser.add_argument("readfile", help="name of read file")
    # parser.add_argument("passed_writefile", 
        # help="name of write file for passed sequences")
    # parser.add_argument("rejected_writefile", 
        # help="name of write file for rejected sequences")

    args = parser.parse_args()
 
    try:
        sorter = Sorter(args)
        sorter.run()
    except:
        exit(1)
