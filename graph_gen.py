import seaborn
import pandas
from matplotlib import pyplot


async def vote_graph(vote_data):
    vote_datetimes = []
    simulated_counts_dict = {}
    start_counts_dict = {}
    simulated_count_time_series = []

    for candidate in vote_data["counts"].keys():
        simulated_counts_dict[candidate] = 0
        start_counts_dict[candidate] = 0

    simulated_count_time_series.append(start_counts_dict)
    vote_datetimes.append(pandas.to_datetime(vote_data["vote_start_datetime"]))

    for vote in vote_data["timestamped_votes"]:
        vote_datetimes.append(pandas.to_datetime(vote["datetime"]))
        del vote["datetime"]
        simulated_counts_dict[vote["votes"][0]] += 10
        simulated_counts_dict[vote["votes"][1]] += 5
        simulated_counts_dict[vote["votes"][2]] -= 5
        simulated_count_time_series.append(dict(simulated_counts_dict))

    vote_dataframe = pandas.DataFrame(data=simulated_count_time_series, index=vote_datetimes)
    # vote_dataframe.loc[vote_data["vote_start_datetime"]] = start_counts_dict

    seaborn.set()
    vote_dataframe.plot(linestyle="-.", linewidth=3)

    pyplot.xlabel("Date Time")
    pyplot.ylabel("FreddiePoints")
    pyplot.legend()
    pyplot.savefig("./vote_visuals/vote_plot.png", dpi=500)


# Old code kept in case it's ever needed:
'''
def gen_vote_graph(vote_record_obj):
    ending_counts[vote_record_obj["votes"][0].lower()] += 10
    ending_counts[vote_record_obj["votes"][1].lower()] += 5
    ending_counts[vote_record_obj["votes"][2].lower()] -= 5
    vote_fig, ax = plt.subplots()
    ax.barh(list(ending_counts.keys()), list(ending_counts.values()), height=0.2, align="edge",
            color="#004b86", edgecolor="black")
    ax.set_title(f"{vote_record_obj['datetime']}")
    ax.set(xlabel="FreddiePoints", ylabel="Candidate")
    vote_fig.canvas.draw()
    tmp_plot_img = np.frombuffer(vote_fig.canvas.tostring_rgb(), dtype="uint8")
    tmp_plot_img = tmp_plot_img.reshape(vote_fig.canvas.get_width_height()[::-1] + (3,))
    return tmp_plot_img

kwargs_write = {"fps": 1.0, "quantizer": "nq"}

imageio.mimsave("./vote_visuals/vote_graph.gif",
                [gen_vote_graph(vote_record) for vote_record in vote_data["timestamped_votes"]], fps=0.5)
'''
